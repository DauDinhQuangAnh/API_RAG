from __future__ import annotations

from API_RAG_NEW.embeddings import EmbeddingCache
from API_RAG_NEW.operations import (
    observe_duration,
    increment,
    normalize_correlation_id,
    render_metrics,
    reset_metrics_for_tests,
)


def test_correlation_id_validation() -> None:
    assert normalize_correlation_id("trace-123") == "trace-123"
    generated = normalize_correlation_id("unsafe\nvalue")
    assert len(generated) == 36


def test_metrics_escape_labels() -> None:
    reset_metrics_for_tests()
    increment("weavecarbon_rag_test_total", value='a"b')
    assert 'weavecarbon_rag_test_total{value="a\\"b"} 1' in render_metrics()


def test_metrics_record_stage_duration(monkeypatch) -> None:
    reset_metrics_for_tests()
    monkeypatch.setattr("API_RAG_NEW.operations.time.perf_counter", lambda: 10.125)

    assert observe_duration("llm_answer", 10.0) == 125.0
    output = render_metrics()
    assert 'weavecarbon_rag_stage_duration_ms_count{stage="llm_answer"} 1' in output
    assert 'weavecarbon_rag_stage_duration_ms_sum{stage="llm_answer"} 125.0' in output


def test_embedding_cache_is_versioned_and_reports_hit_miss() -> None:
    reset_metrics_for_tests()
    cache = EmbeddingCache(maxsize=2)
    key = cache.make_key("model-a", "query", "hello")
    assert cache.get(key) is None
    cache.put(key, [1.0])
    assert cache.get(key) == [1.0]
    output = render_metrics()
    assert 'result="miss"' in output
    assert 'result="hit"' in output
