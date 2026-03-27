from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class IngestResponse(BaseModel):
    collection_name: str
    rows: int
    chunks: int


class CollectionCreateRequest(BaseModel):
    name: str
    description: str | None = None


class CollectionUpdateRequest(BaseModel):
    new_name: str | None = None
    metadata: dict[str, Any] | None = None


class CollectionInfo(BaseModel):
    name: str
    metadata: dict[str, Any] | None = None
    count: int


class QueryRequest(BaseModel):
    query: str
    columns_to_answer: list[str]
    number_docs_retrieval: int = Field(default=3, ge=1, le=50)


class QueryResponse(BaseModel):
    metadatas: list[Any]
    retrieved_data: str
    answer: str
    full_prompt: str


class DirectChatRequest(BaseModel):
    query: str
    api_key: str | None = None


class DirectChatResponse(BaseModel):
    query: str
    answer: str


class CompanyRecommendationRequest(BaseModel):
    company_id: str | None = None
    language: str = "vi"


class CompanyRecommendation(BaseModel):
    id: str
    title: str
    description: str
    impact: str
    reduction: str
    difficulty: str
    category: str


class CompanyRecommendationResponse(BaseModel):
    company_id: str
    recommendations: list[CompanyRecommendation]


class ProductSuggestionRequest(BaseModel):
    product_id: str | None = None
    language: str = "vi"


class ProductSuggestion(BaseModel):
    id: str
    type: str
    title: str
    description: str
    potentialReduction: int
    difficulty: str


class ProductSuggestionResponse(BaseModel):
    product_id: str
    suggestions: list[ProductSuggestion]
