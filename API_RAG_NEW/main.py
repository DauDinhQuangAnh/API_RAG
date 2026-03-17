from __future__ import annotations

import io
import os
import uuid
from typing import List, Optional

import chromadb
import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from chunking import ProtonxSemanticChunker
from constant import GEMINI
from download_model import PRIMARY_MODEL_NAME, ensure_embedding_model
from llms.onlinellms import OnlineLLMs
from search import vector_search
from utils import clean_collection_name, divide_dataframe, process_batch
from database import get_db_connection


load_dotenv()


def _parse_cors_origins(raw_value: str | None) -> list[str]:
    if not raw_value:
        return ["*"]

    origins = [item.strip() for item in raw_value.split(",") if item.strip()]
    return origins or ["*"]


ROOT_PATH = os.getenv("ROOT_PATH", "").strip()
ALLOWED_ORIGINS = _parse_cors_origins(os.getenv("RAG_CORS_ORIGINS"))

app = FastAPI(title="RAG API", version="1.0.0", root_path=ROOT_PATH)


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials="*" not in ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.getenv("CHROMA_DB_PATH", "db")
DEFAULT_EMBEDDING_MODEL = PRIMARY_MODEL_NAME
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

_client = chromadb.PersistentClient(DB_PATH)
_embedding_model, DEFAULT_EMBEDDING_MODEL, _ = ensure_embedding_model(
    preferred_model=DEFAULT_EMBEDDING_MODEL
)


class IngestResponse(BaseModel):
    collection_name: str
    rows: int
    chunks: int


class CollectionCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None


class CollectionUpdateRequest(BaseModel):
    new_name: Optional[str] = None
    metadata: Optional[dict] = None


class CollectionInfo(BaseModel):
    name: str
    metadata: Optional[dict] = None
    count: int


class QueryRequest(BaseModel):
    query: str
    columns_to_answer: List[str]
    number_docs_retrieval: int = Field(default=3, ge=1, le=50)


class QueryResponse(BaseModel):
    metadatas: list
    retrieved_data: str
    answer: str
    full_prompt: str


class DirectChatRequest(BaseModel):
    query: str
    api_key: Optional[str] = None


class DirectChatResponse(BaseModel):
    query: str
    answer: str


class CompanyRecommendationRequest(BaseModel):
    company_id: str
    language: Optional[str] = "vi"


class CompanyRecommendation(BaseModel):
    id: str
    title: str
    description: str
    impact: str  # high/medium/low
    reduction: str  # "15%"
    difficulty: str  # easy/medium/hard
    category: str  # material/transport/production/packaging/compliance/data_quality


class CompanyRecommendationResponse(BaseModel):
    company_id: str
    recommendations: List[CompanyRecommendation]


class ProductSuggestionRequest(BaseModel):
    product_id: str
    language: Optional[str] = "vi"


class ProductSuggestion(BaseModel):
    id: str
    type: str  # material/transport/manufacturing/packaging/end_of_life
    title: str
    description: str
    potentialReduction: int  # percentage
    difficulty: str  # easy/medium/hard


class ProductSuggestionResponse(BaseModel):
    product_id: str
    suggestions: List[ProductSuggestion]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/db/test")
def test_database_connection() -> dict:
    """Test PostgreSQL database connection"""
    db = get_db_connection()
    result = db.test_connection()
    return result


@app.post("/chat/gemini", response_model=DirectChatResponse)
def chat_with_gemini(req: DirectChatRequest) -> DirectChatResponse:
    """
    Chat trực tiếp với Gemini - không cần RAG, không cần collection
    - Nếu không truyền api_key, sẽ dùng GEMINI_API_KEY từ .env
    - Trả về câu trả lời thuần từ Gemini
    """
    api_key = req.api_key or GEMINI_API_KEY
    
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="GEMINI_API_KEY not found. Please provide api_key in request or set in .env file"
        )
    
    try:
        llm = OnlineLLMs(
            name=GEMINI,
            api_key=api_key,
            model_version=GEMINI_MODEL,
        )
        
        answer = llm.generate_content(req.query)
        
        return DirectChatResponse(
            query=req.query,
            answer=answer
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calling Gemini: {str(e)}"
        )


@app.post("/recommendations/company/{company_id}", response_model=CompanyRecommendationResponse)
def generate_company_recommendations(company_id: str, req: CompanyRecommendationRequest) -> CompanyRecommendationResponse:
    """
    Tạo khuyến nghị cải thiện carbon footprint cấp công ty
    - Query PostgreSQL để lấy aggregated company data
    - Phân tích opportunities (materials, transport, production, compliance)
    - Generate 3 recommendations với Gemini
    """
    
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=400, detail="GEMINI_API_KEY not configured")
    
    db = get_db_connection()
    
    try:
        db.connect()
        
        # Query company context
        query = """
        WITH company_stats AS (
          SELECT 
            p.company_id,
            COUNT(p.id) as sku_count,
            SUM(p.total_co2e) as total_co2e,
            SUM(p.materials_co2e) as materials_total,
            SUM(p.production_co2e) as production_total,
            SUM(p.transport_co2e) as transport_total,
            SUM(p.packaging_co2e) as packaging_total,
            AVG(p.data_confidence_score) as avg_confidence,
            COUNT(CASE WHEN p.status = 'active' THEN 1 END)::float / NULLIF(COUNT(*), 0) as published_ratio
          FROM products p
          WHERE p.company_id = %s
          GROUP BY p.company_id
        ),
        carbon_trend AS (
          SELECT 
            year, month, actual_co2e, target_co2e,
            LAG(actual_co2e) OVER (ORDER BY year, month) as prev_month
          FROM carbon_targets
          WHERE company_id = %s
          ORDER BY year DESC, month DESC
          LIMIT 6
        ),
        market_status AS (
          SELECT market_code, readiness_score, status, requirements_missing
          FROM market_readiness
          WHERE company_id = %s
        ),
        top_materials AS (
          SELECT 
            m.name,
            m.category,
            m.default_co2e_per_kg,
            COUNT(pm.id) as usage_count,
            SUM(pm.weight_kg) as total_weight
          FROM product_materials pm
          JOIN materials m ON pm.material_id = m.id
          JOIN products p ON pm.product_id = p.id
          WHERE p.company_id = %s
          GROUP BY m.id, m.name, m.category, m.default_co2e_per_kg
          ORDER BY total_weight DESC
          LIMIT 5
        ),
        transport_analysis AS (
          SELECT 
            sl.transport_mode,
            COUNT(*) as leg_count,
            SUM(sl.co2e) as mode_co2e
          FROM shipment_legs sl
          JOIN shipments s ON sl.shipment_id = s.id
          WHERE s.company_id = %s
          GROUP BY sl.transport_mode
        )
        SELECT json_build_object(
          'stats', (SELECT row_to_json(company_stats.*) FROM company_stats),
          'carbon_trend', (SELECT COALESCE(json_agg(carbon_trend.*), '[]'::json) FROM carbon_trend),
          'markets', (SELECT COALESCE(json_agg(market_status.*), '[]'::json) FROM market_status),
          'top_materials', (SELECT COALESCE(json_agg(top_materials.*), '[]'::json) FROM top_materials),
          'transport', (SELECT COALESCE(json_agg(transport_analysis.*), '[]'::json) FROM transport_analysis)
        ) as context
        """
        
        result = db.execute_query(query, (company_id, company_id, company_id, company_id, company_id))
        
        if not result or not result[0]['context']:
            raise HTTPException(status_code=404, detail="Company data not found")
        
        context = result[0]['context']
        
        # Build system prompt
        system_prompt = """Bạn là chuyên gia tư vấn giảm phát thải carbon cho doanh nghiệp thời trang/dệt may Việt Nam.

## Ngữ cảnh dự án
WeaveCarbon là nền tảng SaaS giúp doanh nghiệp SME ngành thời trang/dệt may Việt Nam đo lường, quản lý và tối ưu hóa dấu chân carbon (carbon footprint) của sản phẩm. Hệ thống hỗ trợ:
- Đánh giá carbon theo vòng đời sản phẩm (LCA): vật liệu, sản xuất, vận chuyển, đóng gói, end-of-life
- Quản lý chuỗi cung ứng và logistics đa chặng (đường bộ, đường biển, đường hàng không, đường sắt)
- Đảm bảo tuân thủ quy định xuất khẩu: EU CBAM, US Climate Act, JP JIS, KR K-ETS
- Theo dõi mục tiêu giảm phát thải theo tháng

Đối tượng người dùng chính là các doanh nghiệp vừa và nhỏ (SME) Việt Nam trong ngành dệt may, có nhu cầu xuất khẩu sang EU, US, Nhật Bản, Hàn Quốc.

## Nhiệm vụ
Dựa trên dữ liệu tổng hợp công ty được cung cấp, hãy đưa ra đúng 3 khuyến nghị chiến lược cấp công ty để giảm carbon footprint.

## Yêu cầu mỗi khuyến nghị:
1. Tiêu đề ngắn gọn (< 50 ký tự)
2. Mô tả cụ thể, hành động được (1-2 câu)
3. Mức độ ảnh hưởng: high/medium/low
4. Phần trăm giảm thiểu dự kiến (ví dụ: "15%")
5. Độ khó thực hiện: easy/medium/hard
6. Danh mục: material/transport/production/packaging/compliance/data_quality

## Nguyên tắc ưu tiên:
- Ưu tiên khuyến nghị có tác động lớn nhất (giảm CO2e nhiều nhất)
- Phù hợp với quy mô và nguồn lực SME Việt Nam
- Khả thi trong 3-6 tháng
- Hỗ trợ mục tiêu xuất khẩu EU/US
- Mỗi khuyến nghị nên thuộc danh mục khác nhau để đa dạng hóa chiến lược

## Format output
Trả về mảng JSON gồm đúng 3 object, mỗi object có các trường: id, title, description, impact, reduction, difficulty, category.

Ví dụ format:
{
  "recommendations": [
    {
      "id": "rec_001",
      "title": "Chuyển sang cotton hữu cơ",
      "description": "Thay thế 50% cotton thông thường bằng cotton hữu cơ cho các dòng sản phẩm chủ lực",
      "impact": "high",
      "reduction": "15%",
      "difficulty": "medium",
      "category": "material"
    }
  ]
}"""
        
        user_prompt = f"Dữ liệu công ty:\n{context}\n\nHãy phân tích và đưa ra 3 khuyến nghị chiến lược."
        
        # Call Gemini
        llm = OnlineLLMs(
            name=GEMINI,
            api_key=GEMINI_API_KEY,
            model_version=GEMINI_MODEL,
        )
        
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        answer = llm.generate_content(full_prompt)
        
        # Parse JSON response
        import json
        import re
        
        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', answer)
        if json_match:
            result_json = json.loads(json_match.group())
            recommendations = result_json.get('recommendations', [])
        else:
            raise HTTPException(status_code=500, detail="Failed to parse AI response")
        
        db.disconnect()
        
        return CompanyRecommendationResponse(
            company_id=company_id,
            recommendations=[CompanyRecommendation(**rec) for rec in recommendations]
        )
        
    except Exception as e:
        db.disconnect()
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")


@app.post("/recommendations/product/{product_id}", response_model=ProductSuggestionResponse)
def generate_product_suggestions(product_id: str, req: ProductSuggestionRequest) -> ProductSuggestionResponse:
    """
    Tạo gợi ý cải thiện carbon footprint cấp sản phẩm
    - Query PostgreSQL để lấy chi tiết sản phẩm
    - Phân tích materials, manufacturing, transport, packaging
    - Generate 3 suggestions với Gemini
    """
    
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=400, detail="GEMINI_API_KEY not configured")
    
    db = get_db_connection()
    
    try:
        db.connect()
        
        # Query product context
        query = """
        SELECT
          -- Product basic
          p.id as product_id,
          p.name as product_name,
          p.category as product_type,
          p.weight_kg * 1000 as weight_grams,
          p.status,

          -- Carbon totals
          p.total_co2e,
          p.materials_co2e,
          p.production_co2e,
          p.transport_co2e,
          p.packaging_co2e,
          p.data_confidence_score,

          -- Company context
          c.target_markets,
          c.business_type,

          -- Materials with factors
          (
            SELECT COALESCE(json_agg(json_build_object(
              'name', m.name,
              'percentage', pm.percentage,
              'emission_factor', m.default_co2e_per_kg,
              'is_recycled', m.is_recycled,
              'certifications', m.certifications,
              'category', m.category
            )), '[]'::json)
            FROM product_materials pm
            JOIN materials m ON pm.material_id = m.id
            WHERE pm.product_id = p.id
          ) as materials,

          -- Transport info
          (
            SELECT COALESCE(json_agg(json_build_object(
              'mode', sl.transport_mode,
              'distance_km', sl.distance_km,
              'co2e', sl.co2e
            )), '[]'::json)
            FROM shipments s
            JOIN shipment_legs sl ON s.id = sl.shipment_id
            JOIN shipment_products sp ON s.id = sp.shipment_id
            WHERE sp.product_id = p.id
          ) as transport_legs

        FROM products p
        JOIN companies c ON p.company_id = c.id
        WHERE p.id = %s
        """
        
        result = db.execute_query(query, (product_id,))
        
        if not result:
            raise HTTPException(status_code=404, detail="Product not found")
        
        product_data = dict(result[0])
        
        # Build system prompt
        system_prompt = """Bạn là chuyên gia tư vấn bền vững cho ngành dệt may Việt Nam.

## Ngữ cảnh dự án
WeaveCarbon là nền tảng SaaS giúp doanh nghiệp SME ngành thời trang/dệt may Việt Nam đo lường, quản lý và tối ưu hóa dấu chân carbon (carbon footprint) của sản phẩm. Hệ thống hỗ trợ:
- Đánh giá carbon theo vòng đời sản phẩm (LCA): vật liệu, sản xuất, vận chuyển, đóng gói, end-of-life
- Quản lý chuỗi cung ứng và logistics đa chặng (đường bộ, đường biển, đường hàng không, đường sắt)
- Đảm bảo tuân thủ quy định xuất khẩu: EU CBAM, US Climate Act, JP JIS, KR K-ETS
- Theo dõi mục tiêu giảm phát thải theo tháng

Đối tượng người dùng chính là các doanh nghiệp vừa và nhỏ (SME) Việt Nam trong ngành dệt may, có nhu cầu xuất khẩu sang EU, US, Nhật Bản, Hàn Quốc.

## Nhiệm vụ
Dựa trên dữ liệu carbon footprint chi tiết của một sản phẩm cụ thể được cung cấp, hãy đưa ra đúng 3 gợi ý cải thiện cấp sản phẩm để giảm carbon footprint.

## Yêu cầu mỗi gợi ý:
1. Tiêu đề ngắn gọn (< 50 ký tự)
2. Mô tả cụ thể, hành động được (action + expected outcome, 1-2 câu)
3. Ước tính % giảm phát thải (số nguyên, dựa trên industry benchmarks)
4. Mức độ khó thực hiện: easy/medium/hard
5. Danh mục: material/transport/manufacturing/packaging/end_of_life

## Nguyên tắc ưu tiên:
- Ưu tiên gợi ý cho giai đoạn phát thải cao nhất
- Phù hợp với quy mô và nguồn lực SME Việt Nam
- Khả thi và có thể hành động ngay
- Xem xét thị trường xuất khẩu để ưu tiên compliance-related suggestions
- Mỗi gợi ý nên thuộc danh mục khác nhau để đa dạng hóa chiến lược

## Format output
Trả về mảng JSON gồm đúng 3 object, mỗi object có các trường: id, type, title, description, potentialReduction, difficulty.

Ví dụ format:
{
  "suggestions": [
    {
      "id": "ai-sug-001",
      "type": "material",
      "title": "Tăng tỷ lệ polyester tái chế",
      "description": "Nâng recycled polyester từ 60% lên 85% có thể giảm 20% phát thải vật liệu",
      "potentialReduction": 12,
      "difficulty": "medium"
    }
  ]
}"""
        
        user_prompt = f"Dữ liệu sản phẩm:\n{product_data}\n\nHãy phân tích và đưa ra 3 gợi ý cải thiện."
        
        # Call Gemini
        llm = OnlineLLMs(
            name=GEMINI,
            api_key=GEMINI_API_KEY,
            model_version=GEMINI_MODEL,
        )
        
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        answer = llm.generate_content(full_prompt)
        
        # Parse JSON response
        import json
        import re
        
        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', answer)
        if json_match:
            result_json = json.loads(json_match.group())
            suggestions = result_json.get('suggestions', [])
        else:
            raise HTTPException(status_code=500, detail="Failed to parse AI response")
        
        db.disconnect()
        
        return ProductSuggestionResponse(
            product_id=product_id,
            suggestions=[ProductSuggestion(**sug) for sug in suggestions]
        )
        
    except Exception as e:
        db.disconnect()
        raise HTTPException(status_code=500, detail=f"Error generating suggestions: {str(e)}")


@app.get("/collections")
def list_collections() -> dict:
    collections = _client.list_collections()
    return {"collections": [c.name for c in collections]}


@app.post("/collections", response_model=CollectionInfo)
def create_collection(req: CollectionCreateRequest) -> CollectionInfo:
    cleaned_name = clean_collection_name(req.name)
    if not cleaned_name:
        raise HTTPException(status_code=400, detail="Invalid collection name.")

    # Check if collection already exists
    try:
        existing = _client.get_collection(name=cleaned_name)
        raise HTTPException(status_code=400, detail="Collection already exists.")
    except Exception:
        # Not found -> safe to create
        pass

    metadata = {"description": req.description} if req.description else {}
    collection = _client.get_or_create_collection(
        name=cleaned_name,
        metadata=metadata or None,
    )
    return CollectionInfo(
        name=collection.name,
        metadata=collection.metadata,
        count=collection.count(),
    )


@app.get("/collections/{collection_name}", response_model=CollectionInfo)
def get_collection_info(collection_name: str) -> CollectionInfo:
    try:
        collection = _client.get_collection(name=collection_name)
    except Exception:
        raise HTTPException(status_code=404, detail="Collection not found.")

    return CollectionInfo(
        name=collection.name,
        metadata=collection.metadata,
        count=collection.count(),
    )


@app.patch("/collections/{collection_name}", response_model=CollectionInfo)
def update_collection(
    collection_name: str, req: CollectionUpdateRequest
) -> CollectionInfo:
    try:
        collection = _client.get_collection(name=collection_name)
    except Exception:
        raise HTTPException(status_code=404, detail="Collection not found.")

    new_name = req.new_name or None
    new_metadata = req.metadata or None

    if not new_name and not new_metadata:
        raise HTTPException(
            status_code=400, detail="Nothing to update (new_name or metadata required)."
        )

    if new_name:
        cleaned = clean_collection_name(new_name)
        if not cleaned:
            raise HTTPException(status_code=400, detail="Invalid new_name.")
        new_name = cleaned

    # Chroma collections support modify for name/metadata.
    collection.modify(name=new_name, metadata=new_metadata)

    # Fetch again in case the reference changed.
    updated = _client.get_collection(name=new_name or collection_name)
    return CollectionInfo(
        name=updated.name,
        metadata=updated.metadata,
        count=updated.count(),
    )


@app.delete("/collections/{collection_name}")
def delete_collection(collection_name: str) -> dict:
    try:
        _client.delete_collection(name=collection_name)
    except Exception:
        raise HTTPException(status_code=404, detail="Collection not found.")
    return {"detail": "Collection deleted successfully."}


@app.post("/ingest", response_model=IngestResponse)
async def ingest_csv(
    file: UploadFile = File(...),
    index_column: str = Form(..., description="Column to index and chunk"),
    collection_name: Optional[str] = Form(None),
) -> IngestResponse:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    raw = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read CSV: {e}")

    if index_column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{index_column}' not found.")

    doc_ids = [str(uuid.uuid4()) for _ in range(len(df))]
    df["doc_id"] = doc_ids

    chunker = ProtonxSemanticChunker(
        model=DEFAULT_EMBEDDING_MODEL,
    )

    chunk_records = []
    for _, row in df.iterrows():
        selected_column_value = row[index_column]
        if not (isinstance(selected_column_value, str) and selected_column_value.strip()):
            continue
        chunks = chunker.split_text(selected_column_value)
        for chunk in chunks:
            chunk_record = {**row.to_dict(), "chunk": chunk}
            chunk_record = {
                "chunk": chunk_record["chunk"],
                **{k: v for k, v in chunk_record.items() if k not in ["chunk", "_id"]},
            }
            chunk_records.append(chunk_record)

    if not chunk_records:
        raise HTTPException(status_code=400, detail="No valid text to chunk.")

    chunks_df = pd.DataFrame(chunk_records)

    if collection_name:
        cleaned = clean_collection_name(collection_name)
        if not cleaned:
            raise HTTPException(status_code=400, detail="Invalid collection_name.")
        final_collection_name = cleaned
    else:
        base = clean_collection_name(os.path.splitext(file.filename)[0]) or "rag_collection"
        final_collection_name = f"rag_collection_{base}_{uuid.uuid4().hex[:6]}"

    collection = _client.get_or_create_collection(
        name=final_collection_name,
        metadata={"description": "A collection for RAG system"},
    )

    batch_size = 256
    df_batches = divide_dataframe(chunks_df, batch_size)
    if not df_batches:
        raise HTTPException(status_code=400, detail="No data available to process.")

    for batch_df in df_batches:
        if batch_df.empty:
            continue
        process_batch(batch_df, _embedding_model, collection)

    return IngestResponse(
        collection_name=final_collection_name,
        rows=len(df),
        chunks=len(chunks_df),
    )


@app.post("/collections/{collection_name}/query", response_model=QueryResponse)
def query_collection(collection_name: str, req: QueryRequest) -> QueryResponse:
    try:
        collection = _client.get_collection(name=collection_name)
    except Exception:
        raise HTTPException(status_code=404, detail="Collection not found.")

    llm = OnlineLLMs(
        name=GEMINI,
        api_key=GEMINI_API_KEY,
        model_version=GEMINI_MODEL,
    )

    metadatas, retrieved_data = vector_search(
        _embedding_model,
        req.query,
        collection,
        req.columns_to_answer,
        req.number_docs_retrieval,
    )

    enhanced_prompt = (
        "Bạn là Weavey, trợ lý AI bền vững của WeaveCarbon hỗ trợ ngành dệt may Việt Nam "
        "bằng tiếng Việt với phong cách thân thiện và chuyên nghiệp, có kiến thức về:\n"
        "- Carbon footprint (Scope 1/2/3, GHG Protocol, emission factors)\n"
        "- Quy định xuất khẩu (EU CBAM, CSRD, US SEC)\n"
        "- Chứng chỉ bền vững (GRS, OEKO-TEX, GOTS, Higg Index)\n"
        "- Logistics và hệ số phát thải vận chuyển\n"
        "- Vật liệu dệt may và emission factors\n\n"
        "Bạn luôn chỉ trả lời các chủ đề liên quan đến: carbon footprint, sustainability, ESG, "
        "quy định xuất khẩu, hướng dẫn dùng WeaveCarbon, chứng chỉ bền vững, logistics và supply chain xanh.\n"
        "Bạn từ chối các chủ đề không liên quan, thông tin cạnh tranh nền tảng khác hoặc tư vấn pháp lý/tài chính cụ thể.\n\n"
        "Khi trả lời:\n"
        "- Dùng bullet points cho hướng dẫn nhiều bước\n"
        "- Cung cấp số liệu cụ thể khi có\n"
        "- Kết thúc bằng câu hỏi follow-up để tiếp tục hỗ trợ người dùng\n\n"
        f'Câu hỏi của người dùng: "{req.query}"\n\n'
        f"Dữ liệu tham khảo:\n{retrieved_data}\n\n"
        "Hãy trả lời câu hỏi dựa trên dữ liệu tham khảo trên."
    )
    answer = llm.generate_content(enhanced_prompt)

    return QueryResponse(
        metadatas=metadatas,
        retrieved_data=retrieved_data,
        answer=answer,
        full_prompt=enhanced_prompt,
    )
