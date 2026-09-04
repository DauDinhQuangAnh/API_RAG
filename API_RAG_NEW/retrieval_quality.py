from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from collections.abc import Sequence
from typing import Protocol


class SearchCandidate(Protocol):
    id: str
    document: str
    distance: float | None
    vector_rank: int


_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "at",
    "be",
    "by",
    "cua",
    "cho",
    "co",
    "duoc",
    "for",
    "from",
    "in",
    "is",
    "la",
    "mot",
    "nhung",
    "of",
    "on",
    "or",
    "the",
    "thi",
    "to",
    "trong",
    "tu",
    "va",
    "voi",
}


def normalize_search_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    without_marks = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return without_marks.casefold().replace("đ", "d")


def search_tokens(text: str) -> list[str]:
    return [
        token
        for token in _TOKEN_PATTERN.findall(normalize_search_text(text))
        if len(token) > 1 and token not in _STOP_WORDS
    ]


def lexical_relevance(query: str, document: str) -> float:
    """Return deterministic query coverage with a small exact-phrase bonus."""
    query_tokens = search_tokens(query)
    document_tokens = search_tokens(document)
    if not query_tokens or not document_tokens:
        return 0.0

    query_counts = Counter(query_tokens)
    document_counts = Counter(document_tokens)
    matched = sum(
        min(count, document_counts.get(token, 0))
        for token, count in query_counts.items()
    )
    coverage = matched / sum(query_counts.values())

    normalized_query = " ".join(query_tokens)
    normalized_document = " ".join(document_tokens)
    phrase_bonus = 0.1 if normalized_query in normalized_document else 0.0
    return min(1.0, coverage + phrase_bonus)


def hybrid_rank_candidate_ids(
    query: str,
    candidates: Sequence[SearchCandidate],
    limit: int,
    *,
    vector_weight: float = 0.40,
    lexical_weight: float = 0.60,
) -> list[str]:
    """Fuse vector order and lexical evidence without an external model call."""
    if limit <= 0:
        return []

    total_weight = vector_weight + lexical_weight
    if total_weight <= 0:
        raise ValueError("Hybrid ranking weights must have a positive total.")

    ranked: list[tuple[float, int, str]] = []
    for fallback_rank, candidate in enumerate(candidates):
        vector_rank = max(0, int(getattr(candidate, "vector_rank", fallback_rank)))
        reciprocal_vector_score = 1.0 / (1.0 + vector_rank)
        lexical_score = lexical_relevance(query, candidate.document)
        score = (
            vector_weight * reciprocal_vector_score
            + lexical_weight * lexical_score
        ) / total_weight
        ranked.append((score, fallback_rank, candidate.id))

    ranked.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [candidate_id for _, _, candidate_id in ranked[:limit]]


def evidence_is_sufficient(
    query: str,
    candidates: Sequence[SearchCandidate],
    *,
    min_lexical_score: float,
    max_distance: float | None,
) -> bool:
    """Require lexical or vector evidence; missing signals fail closed."""
    if not candidates:
        return False

    lexical_scores = [
        lexical_relevance(query, candidate.document) for candidate in candidates
    ]
    if max(lexical_scores, default=0.0) >= max(0.0, min_lexical_score):
        return True

    if max_distance is None or not math.isfinite(max_distance):
        return False
    distances = [
        float(candidate.distance)
        for candidate in candidates
        if isinstance(candidate.distance, (int, float))
        and math.isfinite(float(candidate.distance))
    ]
    return bool(distances) and min(distances) <= max_distance
