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
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

from chunking import ProtonxSemanticChunker
from constant import GEMINI
from llms.onlinellms import OnlineLLMs
from search import vector_search
from utils import clean_collection_name, divide_dataframe, process_batch


load_dotenv()

app = FastAPI(title="RAG API", version="1.0.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.getenv("CHROMA_DB_PATH", "db")
DEFAULT_EMBEDDING_MODEL = "keepitreal/vietnamese-sbert"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

_client = chromadb.PersistentClient(DB_PATH)
_embedding_model = SentenceTransformer(DEFAULT_EMBEDDING_MODEL)


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


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


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