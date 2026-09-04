from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from API_RAG_NEW.retrieval_quality import (
    evidence_is_sufficient,
    hybrid_rank_candidate_ids,
    normalize_search_text,
    search_tokens,
)
from evaluation.stores import (
    ChromaVectorStore,
    EvaluationRecord,
    EvaluationSearchResult,
    EvaluationVectorStore,
    MemoryVectorStore,
    PgVectorStore,
)


DEFAULT_DATASET = REPOSITORY_ROOT / "evaluation" / "datasets" / "compliance_v1.json"
EMBEDDING_DIMENSION = 256
NO_ANSWER_MESSAGE = "Insufficient evidence in the indexed sources to answer this question."


@dataclass(frozen=True)
class EvaluationMetrics:
    answerable_cases: int
    no_answer_cases: int
    recall_at_1: float
    recall_at_3: float
    citation_integrity: float
    grounded_fact_coverage: float
    no_answer_accuracy: float
    latency_p50_ms: float
    latency_p95_ms: float


def load_dataset(path: Path = DEFAULT_DATASET) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    dataset = json.loads(raw.decode("utf-8"))
    _validate_dataset(dataset)
    return dataset, hashlib.sha256(raw).hexdigest()


def deterministic_embedding(text: str, dimension: int = EMBEDDING_DIMENSION) -> list[float]:
    tokens = search_tokens(text)
    features = tokens + [
        f"{tokens[index]}::{tokens[index + 1]}" for index in range(len(tokens) - 1)
    ]
    vector = [0.0] * dimension
    for feature in features:
        digest = hashlib.sha256(feature.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % dimension
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[bucket] += sign
    norm = sum(value * value for value in vector) ** 0.5
    return [value / norm for value in vector] if norm else vector


def build_records(dataset: dict[str, Any]) -> list[EvaluationRecord]:
    return [
        EvaluationRecord(
            id=document["id"],
            document=document["text"],
            embedding=deterministic_embedding(document["text"]),
            metadata={
                **document.get("metadata", {}),
                "source_id": document["source_id"],
                "source": document["source"],
                "doc_id": document["source_id"],
            },
        )
        for document in dataset["documents"]
    ]


def evaluate(
    dataset: dict[str, Any],
    store: EvaluationVectorStore,
    *,
    strategy: str,
    top_k: int = 3,
) -> tuple[EvaluationMetrics, list[dict[str, Any]]]:
    records = build_records(dataset)
    store.replace(records)
    known_sources = {record.metadata["source_id"] for record in records}
    answerable_results: list[dict[str, Any]] = []
    no_answer_results: list[bool] = []
    latencies_ms: list[float] = []
    cases_output: list[dict[str, Any]] = []

    for case in dataset["cases"]:
        started = time.perf_counter()
        candidates = store.search(
            deterministic_embedding(case["query"]),
            limit=max(top_k, len(records)),
        )
        selected = _select_candidates(case["query"], candidates, strategy, top_k)
        should_answer = bool(case["should_answer"])
        has_evidence = True
        if strategy == "hybrid":
            has_evidence = evidence_is_sufficient(
                case["query"],
                selected,
                min_lexical_score=0.12,
                max_distance=None,
            )
        if not has_evidence:
            selected = []
        latency_ms = (time.perf_counter() - started) * 1000
        latencies_ms.append(latency_ms)

        source_ids = [str(item.metadata.get("source_id") or "") for item in selected]
        citation_integrity = all(
            source_id and source_id in known_sources for source_id in source_ids
        )
        context = "\n".join(item.document for item in selected)
        grounded_facts = _grounded_fact_ratio(case["expected_facts"], context)
        expected_sources = set(case["expected_sources"])
        if should_answer:
            answerable_results.append(
                {
                    "expected": expected_sources,
                    "at_1": set(source_ids[:1]),
                    "at_3": set(source_ids[:3]),
                    "citation_integrity": citation_integrity,
                    "grounded_facts": grounded_facts,
                }
            )
        else:
            no_answer_results.append(not selected)

        cases_output.append(
            {
                "case_id": case["id"],
                "should_answer": should_answer,
                "source_ids": source_ids,
                "answer": "evidence available" if selected else NO_ANSWER_MESSAGE,
                "grounded_fact_coverage": grounded_facts,
                "citation_integrity": citation_integrity,
                "latency_ms": round(latency_ms, 4),
            }
        )

    metrics = EvaluationMetrics(
        answerable_cases=len(answerable_results),
        no_answer_cases=len(no_answer_results),
        recall_at_1=_mean_recall(answerable_results, "at_1"),
        recall_at_3=_mean_recall(answerable_results, "at_3"),
        citation_integrity=_mean(
            [float(result["citation_integrity"]) for result in answerable_results]
        ),
        grounded_fact_coverage=_mean(
            [result["grounded_facts"] for result in answerable_results]
        ),
        no_answer_accuracy=_mean([float(value) for value in no_answer_results]),
        latency_p50_ms=round(statistics.median(latencies_ms), 4),
        latency_p95_ms=round(_percentile(latencies_ms, 0.95), 4),
    )
    return metrics, cases_output


def make_store(name: str) -> EvaluationVectorStore:
    if name == "memory":
        return MemoryVectorStore()
    if name == "chroma":
        return ChromaVectorStore()
    if name == "pgvector":
        dsn = os.getenv("RAG_EVAL_PGVECTOR_DSN", "").strip()
        if not dsn:
            raise RuntimeError("RAG_EVAL_PGVECTOR_DSN is required for pgvector.")
        return PgVectorStore(dsn, EMBEDDING_DIMENSION)
    raise ValueError(f"Unsupported evaluation store: {name}")


def run_benchmark(
    dataset_path: Path,
    stores: list[str],
    strategies: list[str],
    *,
    require_stores: bool,
) -> dict[str, Any]:
    dataset, dataset_hash = load_dataset(dataset_path)
    results: dict[str, Any] = {}
    skipped: dict[str, str] = {}
    for store_name in stores:
        try:
            store = make_store(store_name)
        except Exception as exc:
            if require_stores:
                raise
            skipped[store_name] = f"{type(exc).__name__}: {exc}"
            continue
        try:
            results[store_name] = {}
            for strategy in strategies:
                metrics, cases = evaluate(dataset, store, strategy=strategy)
                results[store_name][strategy] = {
                    "metrics": asdict(metrics),
                    "cases": cases,
                }
        finally:
            store.close()

    return {
        "dataset_id": dataset["dataset_id"],
        "dataset_schema_version": dataset["schema_version"],
        "dataset_sha256": dataset_hash,
        "embedding": {
            "type": "deterministic-feature-hash",
            "dimension": EMBEDDING_DIMENSION,
            "paid_api_calls": 0,
        },
        "results": results,
        "skipped_stores": skipped,
    }


def assert_quality_gate(report: dict[str, Any]) -> None:
    for store_name, strategies in report["results"].items():
        final = strategies.get("hybrid", {}).get("metrics")
        if not final:
            continue
        thresholds = {
            "recall_at_1": 0.8,
            "recall_at_3": 1.0,
            "citation_integrity": 1.0,
            "grounded_fact_coverage": 1.0,
            "no_answer_accuracy": 1.0,
        }
        failures = [
            f"{name}={final[name]:.4f} < {minimum:.4f}"
            for name, minimum in thresholds.items()
            if final[name] < minimum
        ]
        if failures:
            raise AssertionError(f"{store_name} quality gate failed: " + "; ".join(failures))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--stores", nargs="+", choices=("memory", "chroma", "pgvector"), default=["memory"]
    )
    parser.add_argument(
        "--strategies", nargs="+", choices=("vector", "hybrid"), default=["vector", "hybrid"]
    )
    parser.add_argument("--require-stores", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    report = run_benchmark(
        args.dataset,
        args.stores,
        args.strategies,
        require_stores=args.require_stores,
    )
    if args.check:
        assert_quality_gate(report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _select_candidates(
    query: str,
    candidates: list[EvaluationSearchResult],
    strategy: str,
    top_k: int,
) -> list[EvaluationSearchResult]:
    if strategy == "vector":
        return candidates[:top_k]
    ranked_ids = hybrid_rank_candidate_ids(query, candidates, top_k)
    by_id = {candidate.id: candidate for candidate in candidates}
    return [by_id[candidate_id] for candidate_id in ranked_ids]


def _grounded_fact_ratio(expected_facts: list[str], context: str) -> float:
    if not expected_facts:
        return 1.0
    normalized_context = normalize_search_text(context)
    supported = sum(
        1 for fact in expected_facts if normalize_search_text(fact) in normalized_context
    )
    return supported / len(expected_facts)


def _mean_recall(results: list[dict[str, Any]], key: str) -> float:
    return _mean(
        [
            len(result["expected"] & result[key]) / len(result["expected"])
            for result in results
            if result["expected"]
        ]
    )


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 1.0


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def _validate_dataset(dataset: dict[str, Any]) -> None:
    if dataset.get("schema_version") != 1:
        raise ValueError("Unsupported evaluation dataset schema version.")
    documents = dataset.get("documents")
    cases = dataset.get("cases")
    if not isinstance(documents, list) or not documents:
        raise ValueError("Evaluation dataset must contain documents.")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Evaluation dataset must contain cases.")
    document_ids = [document.get("id") for document in documents]
    source_ids = [document.get("source_id") for document in documents]
    if any(not document_id for document_id in document_ids) or len(document_ids) != len(
        set(document_ids)
    ):
        raise ValueError("Document id values must be non-empty and unique.")
    if any(not source_id for source_id in source_ids):
        raise ValueError("Document source_id values must be non-empty.")
    known_sources = set(source_ids)
    for case in cases:
        expected_sources = set(case.get("expected_sources", []))
        if not expected_sources <= known_sources:
            raise ValueError(f"Case {case.get('id')} references an unknown source.")
        if bool(case.get("should_answer")) != bool(expected_sources):
            raise ValueError(f"Case {case.get('id')} has inconsistent answer expectations.")


if __name__ == "__main__":
    raise SystemExit(main())
