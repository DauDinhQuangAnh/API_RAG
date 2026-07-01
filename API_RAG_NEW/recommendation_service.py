from __future__ import annotations

import json
import re
from typing import Any

from fastapi import HTTPException

from llms.onlinellms import OnlineLLMs

from API_RAG_NEW.config import GEMINI_MODEL, get_gemini_api_key
from API_RAG_NEW.schemas import (
    CompanyRecommendation,
    CompanyRecommendationRequest,
    CompanyRecommendationResponse,
    DirectChatRequest,
    DirectChatResponse,
    ProductSuggestion,
    ProductSuggestionRequest,
    ProductSuggestionResponse,
)


JSON_OBJECT_PATTERN = re.compile(r"\{[\s\S]*\}")


def chat_with_gemini(req: DirectChatRequest) -> DirectChatResponse:
    llm = _build_llm(api_key=req.api_key)
    answer = llm.generate_content(req.query)
    return DirectChatResponse(query=req.query, answer=answer)


def generate_company_recommendations(
    company_id: str,
    req: CompanyRecommendationRequest,
) -> CompanyRecommendationResponse:
    _validate_path_identifier(company_id, req.company_id, "company_id")
    prompt = (
        "Bạn là chuyên gia carbon và CBAM cho doanh nghiệp xuất khẩu.\n"
        "Hãy đề xuất 3 hành động giảm phát thải có thể áp dụng cho công ty này.\n"
        "Trả về JSON object có khóa recommendations; mỗi item gồm id, title, "
        "description, impact, reduction, difficulty, category.\n"
        f"Ngôn ngữ: {req.language}.\n"
        f"Company id: {company_id}."
    )
    payload = _try_generate_json(prompt)
    recommendations = _parse_company_recommendations(payload)
    return CompanyRecommendationResponse(
        company_id=company_id,
        recommendations=recommendations,
    )


def generate_product_suggestions(
    product_id: str,
    req: ProductSuggestionRequest,
) -> ProductSuggestionResponse:
    _validate_path_identifier(product_id, req.product_id, "product_id")
    prompt = (
        "Bạn là chuyên gia đánh giá vòng đời sản phẩm textile/apparel.\n"
        "Hãy đề xuất 3 cải tiến giảm phát thải cho sản phẩm này.\n"
        "Trả về JSON object có khóa suggestions; mỗi item gồm id, type, title, "
        "description, potentialReduction, difficulty.\n"
        f"Ngôn ngữ: {req.language}.\n"
        f"Product id: {product_id}."
    )
    payload = _try_generate_json(prompt)
    suggestions = _parse_product_suggestions(payload)
    return ProductSuggestionResponse(product_id=product_id, suggestions=suggestions)


def _build_llm(api_key: str | None = None) -> OnlineLLMs:
    resolved_api_key = api_key or get_gemini_api_key()
    if not resolved_api_key:
        raise HTTPException(status_code=400, detail="GEMINI_API_KEY not configured")

    return OnlineLLMs(
        name="gemini",
        api_key=resolved_api_key,
        model_version=GEMINI_MODEL,
    )


def _try_generate_json(prompt: str) -> dict[str, Any]:
    try:
        text = _build_llm().generate_content(prompt)
        return _extract_json_payload(text)
    except Exception:
        return {}


def _extract_json_payload(text: str) -> dict[str, Any]:
    match = JSON_OBJECT_PATTERN.search(text or "")
    if not match:
        return {}
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _validate_path_identifier(
    path_value: str,
    body_value: str | None,
    field_name: str,
) -> None:
    if body_value and body_value != path_value:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} in path and body must match.",
        )


def _parse_company_recommendations(
    payload: dict[str, Any],
) -> list[CompanyRecommendation]:
    raw_items = payload.get("recommendations")
    if not isinstance(raw_items, list) or not raw_items:
        raw_items = [
            {
                "id": "energy-audit",
                "title": "Rà soát năng lượng sản xuất",
                "description": "Ưu tiên đo điện, hơi, nhiên liệu theo công đoạn để giảm phụ thuộc vào proxy.",
                "impact": "high",
                "reduction": "5-12%",
                "difficulty": "medium",
                "category": "production",
            },
            {
                "id": "supplier-data",
                "title": "Thu thập dữ liệu nhà cung ứng",
                "description": "Yêu cầu chứng từ vật liệu, nguồn gốc và hệ số phát thải từ nhà cung ứng chính.",
                "impact": "medium",
                "reduction": "3-8%",
                "difficulty": "easy",
                "category": "materials",
            },
            {
                "id": "route-optimization",
                "title": "Tối ưu tuyến vận chuyển",
                "description": "So sánh đường bộ, đường biển, đường sắt và gom lô để giảm phát thải logistics.",
                "impact": "medium",
                "reduction": "2-6%",
                "difficulty": "medium",
                "category": "transport",
            },
        ]

    return [
        CompanyRecommendation(
            id=str(item.get("id") or f"recommendation-{index + 1}"),
            title=str(item.get("title") or f"Recommendation {index + 1}"),
            description=str(item.get("description") or ""),
            impact=str(item.get("impact") or "medium"),
            reduction=str(item.get("reduction") or "0%"),
            difficulty=str(item.get("difficulty") or "medium"),
            category=str(item.get("category") or "general"),
        )
        for index, item in enumerate(raw_items[:5])
        if isinstance(item, dict)
    ]


def _parse_product_suggestions(payload: dict[str, Any]) -> list[ProductSuggestion]:
    raw_items = payload.get("suggestions")
    if not isinstance(raw_items, list) or not raw_items:
        raw_items = [
            {
                "id": "recycled-material",
                "type": "materials",
                "title": "Tăng tỷ lệ vật liệu tái chế",
                "description": "Thử thay một phần vật liệu virgin bằng vật liệu tái chế có chứng nhận.",
                "potentialReduction": 10,
                "difficulty": "medium",
            },
            {
                "id": "energy-metering",
                "type": "production",
                "title": "Tách số đo năng lượng theo công đoạn",
                "description": "Đo điện/nhiên liệu theo line sản xuất để cải thiện độ tin cậy tính toán.",
                "potentialReduction": 7,
                "difficulty": "easy",
            },
            {
                "id": "logistics-mode",
                "type": "transport",
                "title": "So sánh phương thức vận chuyển",
                "description": "Ưu tiên tuyến ít carbon hơn khi thời gian giao hàng cho phép.",
                "potentialReduction": 5,
                "difficulty": "medium",
            },
        ]

    return [
        ProductSuggestion(
            id=str(item.get("id") or f"suggestion-{index + 1}"),
            type=str(item.get("type") or "general"),
            title=str(item.get("title") or f"Suggestion {index + 1}"),
            description=str(item.get("description") or ""),
            potentialReduction=int(item.get("potentialReduction") or 0),
            difficulty=str(item.get("difficulty") or "medium"),
        )
        for index, item in enumerate(raw_items[:5])
        if isinstance(item, dict)
    ]
