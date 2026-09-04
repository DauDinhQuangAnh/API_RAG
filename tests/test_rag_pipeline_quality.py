from __future__ import annotations

from contextlib import nullcontext

from API_RAG_NEW import rag_pipeline


class FakeCollection:
    def __init__(self, document: str, distance: float = 1.4) -> None:
        self.document = document
        self.distance = distance

    def query(self, **_kwargs):
        return {
            "ids": [["record-1"]],
            "documents": [[self.document]],
            "metadatas": [[{"source": "fixture.md", "doc_id": "fixture-1"}]],
            "distances": [[self.distance]],
        }


def test_vector_search_returns_empty_context_when_evidence_is_insufficient(
    monkeypatch,
) -> None:
    monkeypatch.setattr(rag_pipeline, "encode_queries", lambda *_args: [[1.0, 0.0]])
    monkeypatch.setattr(rag_pipeline, "acquire_embedding_slot", nullcontext)

    metadatas, context = rag_pipeline.vector_search(
        object(),
        "What is tomorrow's weather in Bangkok?",
        FakeCollection("CBAM reporting evidence for imported cement"),
        3,
        enable_evidence_guard=True,
        min_lexical_evidence_score=0.12,
    )

    assert metadatas == [[]]
    assert context == ""


def test_vector_search_preserves_source_metadata_for_supported_evidence(
    monkeypatch,
) -> None:
    monkeypatch.setattr(rag_pipeline, "encode_queries", lambda *_args: [[1.0, 0.0]])
    monkeypatch.setattr(rag_pipeline, "acquire_embedding_slot", nullcontext)

    metadatas, context = rag_pipeline.vector_search(
        object(),
        "Which CBAM reporting evidence covers imported cement?",
        FakeCollection("CBAM reporting evidence for imported cement", distance=0.2),
        1,
        reranker_type="hybrid",
        enable_evidence_guard=True,
        min_lexical_evidence_score=0.12,
    )

    assert metadatas[0][0]["source"] == "fixture.md"
    assert metadatas[0][0]["doc_id"] == "fixture-1"
    assert "source=fixture.md" in context
