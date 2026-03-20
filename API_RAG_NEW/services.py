from __future__ import annotations

import io
import json
import os
import re
import uuid
from typing import Any

import pandas as pd
from fastapi import HTTPException

from chunking import ProtonxSemanticChunker
from database import get_db_connection
from llms.onlinellms import OnlineLLMs

from API_RAG_NEW.config import (
    CHROMA_CLIENT,
    DEFAULT_COLLECTION_DESCRIPTION,
    EMBEDDING_MODEL,
    GEMINI_MODEL,
    GEMINI_PROVIDER,
    INGEST_BATCH_SIZE,
    get_gemini_api_key,
)
from API_RAG_NEW.rag_pipeline import (
    add_records_to_collection,
    clean_collection_name,
    vector_search,
)
from API_RAG_NEW.schemas import (
    CollectionCreateRequest,
    CollectionInfo,
    CollectionUpdateRequest,
    CompanyRecommendation,
    CompanyRecommendationRequest,
    CompanyRecommendationResponse,
    DirectChatRequest,
    DirectChatResponse,
    IngestResponse,
    ProductSuggestion,
    ProductSuggestionRequest,
    ProductSuggestionResponse,
    QueryRequest,
    QueryResponse,
)


JSON_OBJECT_PATTERN = re.compile(r"\{[\s\S]*\}")

COMPANY_CONTEXT_QUERY = """
WITH company_stats AS (
  SELECT
    p.company_id,
    COUNT(p.id) AS sku_count,
    SUM(p.total_co2e) AS total_co2e,
    SUM(p.materials_co2e) AS materials_total,
    SUM(p.production_co2e) AS production_total,
    SUM(p.transport_co2e) AS transport_total,
    SUM(p.packaging_co2e) AS packaging_total,
    AVG(p.data_confidence_score) AS avg_confidence,
    COUNT(CASE WHEN p.status = 'active' THEN 1 END)::float / NULLIF(COUNT(*), 0) AS published_ratio
  FROM products p
  WHERE p.company_id = %s
  GROUP BY p.company_id
),
carbon_trend AS (
  SELECT
    year,
    month,
    actual_co2e,
    target_co2e,
    LAG(actual_co2e) OVER (ORDER BY year, month) AS prev_month
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
    COUNT(pm.id) AS usage_count,
    SUM(pm.weight_kg) AS total_weight
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
    COUNT(*) AS leg_count,
    SUM(sl.co2e) AS mode_co2e
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
) AS context
"""

PRODUCT_CONTEXT_QUERY = """
SELECT
  p.id AS product_id,
  p.name AS product_name,
  p.category AS product_type,
  p.weight_kg * 1000 AS weight_grams,
  p.status,
  p.total_co2e,
  p.materials_co2e,
  p.production_co2e,
  p.transport_co2e,
  p.packaging_co2e,
  p.data_confidence_score,
  c.target_markets,
  c.business_type,
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
  ) AS materials,
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
  ) AS transport_legs
FROM products p
JOIN companies c ON p.company_id = c.id
WHERE p.id = %s
"""


def health_payload() -> dict[str, str]:
    return {"status": "ok"}


def test_database_connection() -> dict[str, Any]:
    return get_db_connection().test_connection()


def chat_with_gemini(req: DirectChatRequest) -> DirectChatResponse:
    llm = _build_llm(api_key=req.api_key)
    answer = llm.generate_content(req.query)
    return DirectChatResponse(query=req.query, answer=answer)


def generate_company_recommendations(
    company_id: str, req: CompanyRecommendationRequest
) -> CompanyRecommendationResponse:
    _validate_path_identifier(company_id, req.company_id, "company_id")

    rows = _run_query(
        COMPANY_CONTEXT_QUERY,
        (company_id, company_id, company_id, company_id, company_id),
    )
    if not rows or not rows[0].get("context"):
        raise HTTPException(status_code=404, detail="Company data not found")

    prompt = _build_company_prompt(rows[0]["context"], req.language)
    payload = _extract_json_payload(_build_llm().generate_content(prompt))
    recommendations = _parse_company_recommendations(payload)
    return CompanyRecommendationResponse(
        company_id=company_id,
        recommendations=recommendations,
    )


def generate_product_suggestions(
    product_id: str, req: ProductSuggestionRequest
) -> ProductSuggestionResponse:
    _validate_path_identifier(product_id, req.product_id, "product_id")

    rows = _run_query(PRODUCT_CONTEXT_QUERY, (product_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Product not found")

    prompt = _build_product_prompt(dict(rows[0]), req.language)
    payload = _extract_json_payload(_build_llm().generate_content(prompt))
    suggestions = _parse_product_suggestions(payload)
    return ProductSuggestionResponse(product_id=product_id, suggestions=suggestions)


def list_collections() -> dict[str, list[str]]:
    collections = CHROMA_CLIENT.list_collections()
    return {"collections": [collection.name for collection in collections]}


def create_collection(req: CollectionCreateRequest) -> CollectionInfo:
    cleaned_name = clean_collection_name(req.name)
    if not cleaned_name:
        raise HTTPException(status_code=400, detail="Invalid collection name.")

    existing_names = {collection.name for collection in CHROMA_CLIENT.list_collections()}
    if cleaned_name in existing_names:
        raise HTTPException(status_code=400, detail="Collection already exists.")

    metadata = {"description": req.description} if req.description else None
    collection = CHROMA_CLIENT.get_or_create_collection(
        name=cleaned_name,
        metadata=metadata,
    )
    return _to_collection_info(collection)


def get_collection_info(collection_name: str) -> CollectionInfo:
    return _to_collection_info(_get_collection_or_404(collection_name))


def update_collection(
    collection_name: str, req: CollectionUpdateRequest
) -> CollectionInfo:
    collection = _get_collection_or_404(collection_name)
    new_name = req.new_name or None
    new_metadata = req.metadata or None

    if not new_name and not new_metadata:
        raise HTTPException(
            status_code=400,
            detail="Nothing to update (new_name or metadata required).",
        )

    if new_name:
        cleaned_name = clean_collection_name(new_name)
        if not cleaned_name:
            raise HTTPException(status_code=400, detail="Invalid new_name.")
        new_name = cleaned_name

    collection.modify(name=new_name, metadata=new_metadata)
    return _to_collection_info(_get_collection_or_404(new_name or collection_name))


def delete_collection(collection_name: str) -> dict[str, str]:
    _get_collection_or_404(collection_name)
    CHROMA_CLIENT.delete_collection(name=collection_name)
    return {"detail": "Collection deleted successfully."}


def ingest_csv_content(
    file_name: str,
    raw_content: bytes,
    index_column: str,
    requested_collection_name: str | None,
) -> IngestResponse:
    if not file_name.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    try:
        dataframe = pd.read_csv(io.BytesIO(raw_content))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read CSV: {exc}") from exc

    if index_column not in dataframe.columns:
        raise HTTPException(
            status_code=400,
            detail=f"Column '{index_column}' not found.",
        )

    dataframe = dataframe.copy()
    dataframe["doc_id"] = [str(uuid.uuid4()) for _ in range(len(dataframe))]

    final_collection_name = _resolve_collection_name(file_name, requested_collection_name)
    collection = CHROMA_CLIENT.get_or_create_collection(
        name=final_collection_name,
        metadata={"description": DEFAULT_COLLECTION_DESCRIPTION},
    )

    chunker = ProtonxSemanticChunker(model=EMBEDDING_MODEL)
    pending_records: list[dict[str, Any]] = []
    chunk_count = 0

    for record in _iter_chunk_records(dataframe, index_column, chunker):
        pending_records.append(record)
        if len(pending_records) >= INGEST_BATCH_SIZE:
            chunk_count += add_records_to_collection(
                pending_records,
                EMBEDDING_MODEL,
                collection,
            )
            pending_records.clear()

    if pending_records:
        chunk_count += add_records_to_collection(
            pending_records,
            EMBEDDING_MODEL,
            collection,
        )

    if chunk_count == 0:
        raise HTTPException(status_code=400, detail="No valid text to chunk.")

    return IngestResponse(
        collection_name=final_collection_name,
        rows=len(dataframe),
        chunks=chunk_count,
    )


def query_collection(collection_name: str, req: QueryRequest) -> QueryResponse:
    collection = _get_collection_or_404(collection_name)
    metadatas, retrieved_data = vector_search(
        EMBEDDING_MODEL,
        req.query,
        collection,
        req.columns_to_answer,
        req.number_docs_retrieval,
    )
    full_prompt = _build_query_prompt(req.query, retrieved_data)
    answer = _build_llm().generate_content(full_prompt)
    return QueryResponse(
        metadatas=metadatas,
        retrieved_data=retrieved_data,
        answer=answer,
        full_prompt=full_prompt,
    )


def _build_llm(api_key: str | None = None) -> OnlineLLMs:
    resolved_api_key = api_key or get_gemini_api_key()
    if not resolved_api_key:
        raise HTTPException(status_code=400, detail="GEMINI_API_KEY not configured")

    return OnlineLLMs(
        name=GEMINI_PROVIDER,
        api_key=resolved_api_key,
        model_version=GEMINI_MODEL,
    )


def _build_company_prompt(context: Any, language: str) -> str:
    return (
        "You are a carbon-reduction advisor for Vietnamese textile and fashion SMEs "
        "using WeaveCarbon.\n"
        "Return exactly 3 company-level recommendations as JSON only.\n"
        f"Output language: {language}.\n"
        "Prioritize the highest-impact actions supported by the data, keep them realistic "
        "for SME execution in 3-6 months, and diversify categories when possible.\n"
        "JSON schema:\n"
        "{\n"
        '  "recommendations": [\n'
        "    {\n"
        '      "id": "rec_001",\n'
        '      "title": "...",\n'
        '      "description": "...",\n'
        '      "impact": "high|medium|low",\n'
        '      "reduction": "15%",\n'
        '      "difficulty": "easy|medium|hard",\n'
        '      "category": "material|transport|production|packaging|compliance|data_quality"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        f"Company context:\n{context}"
    )


def _build_product_prompt(product_data: dict[str, Any], language: str) -> str:
    return (
        "You are a sustainability advisor for Vietnamese textile and fashion SMEs "
        "using WeaveCarbon.\n"
        "Return exactly 3 product-level improvement suggestions as JSON only.\n"
        f"Output language: {language}.\n"
        "Prioritize the lifecycle stages with the highest emissions, keep suggestions "
        "practical for SMEs, and prefer different categories when possible.\n"
        "JSON schema:\n"
        "{\n"
        '  "suggestions": [\n'
        "    {\n"
        '      "id": "sug_001",\n'
        '      "type": "material|transport|manufacturing|packaging|end_of_life",\n'
        '      "title": "...",\n'
        '      "description": "...",\n'
        '      "potentialReduction": 12,\n'
        '      "difficulty": "easy|medium|hard"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        f"Product context:\n{product_data}"
    )


def _build_query_prompt(query: str, retrieved_data: str) -> str:
    return (
        "You are Weavey, the WeaveCarbon sustainability assistant for Vietnamese "
        "textile and apparel teams.\n"
        "Answer only questions related to carbon footprint, sustainability, ESG, "
        "materials, certifications, export compliance, logistics, or green supply chains.\n"
        "If the question is outside this scope, politely refuse.\n"
        "Answer in Vietnamese, use bullet points when useful, cite specific details from "
        "the reference data when available, and end with one short follow-up question.\n\n"
        f"User question: {query}\n\n"
        f"Reference data:\n{retrieved_data}"
    )


def _extract_json_payload(answer: str) -> dict[str, Any]:
    match = JSON_OBJECT_PATTERN.search(answer)
    if not match:
        raise HTTPException(status_code=500, detail="Failed to parse AI response")

    try:
        return json.loads(match.group())
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="Failed to parse AI response") from exc


def _parse_company_recommendations(
    payload: dict[str, Any]
) -> list[CompanyRecommendation]:
    try:
        recommendations = [
            CompanyRecommendation(**item)
            for item in payload.get("recommendations", [])
        ]
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid recommendation format: {exc}",
        ) from exc

    if not recommendations:
        raise HTTPException(status_code=500, detail="AI returned no recommendations")

    return recommendations[:3]


def _parse_product_suggestions(payload: dict[str, Any]) -> list[ProductSuggestion]:
    try:
        suggestions = [
            ProductSuggestion(**item)
            for item in payload.get("suggestions", [])
        ]
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid suggestion format: {exc}",
        ) from exc

    if not suggestions:
        raise HTTPException(status_code=500, detail="AI returned no suggestions")

    return suggestions[:3]


def _get_collection_or_404(collection_name: str) -> Any:
    try:
        return CHROMA_CLIENT.get_collection(name=collection_name)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Collection not found.") from exc


def _to_collection_info(collection: Any) -> CollectionInfo:
    return CollectionInfo(
        name=collection.name,
        metadata=collection.metadata,
        count=collection.count(),
    )


def _run_query(query: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    with get_db_connection() as db:
        return db.execute_query(query, params)


def _validate_path_identifier(
    path_value: str, body_value: str | None, field_name: str
) -> None:
    if body_value and body_value != path_value:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} in path and body must match.",
        )


def _resolve_collection_name(
    file_name: str, requested_collection_name: str | None
) -> str:
    if requested_collection_name:
        cleaned_name = clean_collection_name(requested_collection_name)
        if not cleaned_name:
            raise HTTPException(status_code=400, detail="Invalid collection_name.")
        return cleaned_name

    base_name = clean_collection_name(os.path.splitext(file_name)[0]) or "rag_collection"
    return f"rag_collection_{base_name}_{uuid.uuid4().hex[:6]}"


def _iter_chunk_records(
    dataframe: pd.DataFrame,
    index_column: str,
    chunker: ProtonxSemanticChunker,
):
    for _, row in dataframe.iterrows():
        row_data = {
            key: _normalize_dataframe_value(value)
            for key, value in row.to_dict().items()
        }
        text = row_data.get(index_column)
        if not isinstance(text, str) or not text.strip():
            continue

        for chunk in chunker.split_text(text):
            if not chunk.strip():
                continue
            yield {
                "chunk": chunk,
                **{
                    key: value
                    for key, value in row_data.items()
                    if key not in {"chunk", "_id"}
                },
            }


def _normalize_dataframe_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    return value
