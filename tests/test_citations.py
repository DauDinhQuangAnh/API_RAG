from __future__ import annotations

from API_RAG_NEW.citations import build_citations_from_metadatas


def test_citations_preserve_real_source_identifiers_and_skip_unknown_sources() -> None:
    citations = build_citations_from_metadatas(
        [
            {"chunk": "must not become a citation"},
            {
                "source_id": "eu-cbam-scope",
                "doc_id": "doc-123",
                "source": "eu-cbam-scope.md",
                "page_number": 4,
                "chunk": "Covered product evidence",
            },
        ]
    )

    assert len(citations) == 1
    assert citations[0].id == 1
    assert citations[0].source_id == "eu-cbam-scope"
    assert citations[0].doc_id == "doc-123"
    assert citations[0].source == "eu-cbam-scope.md"


def test_citation_builder_never_invents_a_source_identifier() -> None:
    citation = build_citations_from_metadatas(
        [{"source": "known-source.pdf", "chunk": "Evidence"}]
    )[0]

    assert citation.source == "known-source.pdf"
    assert citation.source_id is None
    assert citation.doc_id is None
