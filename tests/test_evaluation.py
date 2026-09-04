from __future__ import annotations

from evaluation.runner import assert_quality_gate, evaluate, load_dataset
from evaluation.stores import MemoryVectorStore


def test_versioned_dataset_passes_offline_quality_gate() -> None:
    dataset, dataset_hash = load_dataset()
    assert dataset["dataset_id"] == "weavecarbon-compliance-v1"
    assert len(dataset_hash) == 64

    store = MemoryVectorStore()
    baseline, _ = evaluate(dataset, store, strategy="vector")
    final, cases = evaluate(dataset, store, strategy="hybrid")

    assert baseline.no_answer_accuracy == 0.0
    assert final.recall_at_3 == 1.0
    assert final.grounded_fact_coverage == 1.0
    assert final.citation_integrity == 1.0
    assert final.no_answer_accuracy == 1.0
    assert all(
        case["source_ids"] == []
        for case in cases
        if not case["should_answer"]
    )

    assert_quality_gate(
        {"results": {"memory": {"hybrid": {"metrics": final.__dict__}}}}
    )
