from __future__ import annotations

from dataclasses import dataclass

from API_RAG_NEW.retrieval_quality import (
    evidence_is_sufficient,
    hybrid_rank_candidate_ids,
    lexical_relevance,
    search_tokens,
)


@dataclass(frozen=True)
class Candidate:
    id: str
    document: str
    distance: float | None
    vector_rank: int


def test_search_tokens_are_accent_insensitive_and_remove_stop_words() -> None:
    assert search_tokens("Dữ liệu phát thải của tổ chức") == [
        "du",
        "lieu",
        "phat",
        "thai",
        "chuc",
    ]


def test_hybrid_rank_uses_lexical_evidence_to_correct_vector_order() -> None:
    candidates = [
        Candidate("wrong", "unrelated textile supplier record", 0.1, 0),
        Candidate("right", "CBAM definitive period starts January 2026", 0.2, 1),
    ]

    assert hybrid_rank_candidate_ids(
        "When does the CBAM definitive period start?", candidates, 2
    )[0] == "right"


def test_evidence_guard_fails_closed_without_lexical_or_vector_support() -> None:
    candidates = [Candidate("weather", "utility invoice reporting period", 1.4, 0)]

    assert not evidence_is_sufficient(
        "What is tomorrow's weather in Bangkok?",
        candidates,
        min_lexical_score=0.12,
        max_distance=1.0,
    )
    assert evidence_is_sufficient(
        "Which utility invoice is evidence?",
        candidates,
        min_lexical_score=0.12,
        max_distance=None,
    )


def test_lexical_relevance_is_bounded() -> None:
    assert lexical_relevance("CBAM report", "CBAM report") == 1.0
    assert lexical_relevance("weather Bangkok", "CBAM report") == 0.0
