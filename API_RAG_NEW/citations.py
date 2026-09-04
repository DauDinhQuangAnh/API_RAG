from __future__ import annotations

from typing import Any

from API_RAG_NEW.schemas import Citation


MAX_CITATION_SNIPPET_CHARS = 300


def build_citations_from_metadatas(
    metadatas: list[dict[str, Any]],
) -> list[Citation]:
    citations: list[Citation] = []
    for metadata in metadatas:
        normalized_metadata = metadata if isinstance(metadata, dict) else {}
        source_id = _optional_str(normalized_metadata.get("source_id"))
        doc_id = _optional_str(normalized_metadata.get("doc_id"))
        source = _optional_str(normalized_metadata.get("source"))
        if source_id is None and doc_id is None and source is None:
            continue
        citations.append(
            Citation(
                id=len(citations) + 1,
                source_id=source_id,
                source=source,
                source_type=_optional_str(normalized_metadata.get("source_type")),
                page_number=_optional_int(normalized_metadata.get("page_number")),
                chunk_index=_optional_int(normalized_metadata.get("chunk_index")),
                page_chunk_index=_optional_int(
                    normalized_metadata.get("page_chunk_index")
                ),
                row_index=_optional_int(normalized_metadata.get("row_index")),
                row_chunk_index=_optional_int(
                    normalized_metadata.get("row_chunk_index")
                ),
                doc_id=doc_id,
                section_title=_optional_str(
                    normalized_metadata.get("section_title")
                ),
                section_path=_optional_str(normalized_metadata.get("section_path")),
                chunk_type=_optional_str(normalized_metadata.get("chunk_type")),
                table_index=_optional_int(normalized_metadata.get("table_index")),
                table_title=_optional_str(normalized_metadata.get("table_title")),
                table_row_index=_optional_int(
                    normalized_metadata.get("table_row_index")
                ),
                snippet=_snippet(str(normalized_metadata.get("chunk") or "")),
            )
        )
    return citations


def _snippet(text: str, max_chars: int = MAX_CITATION_SNIPPET_CHARS) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars].rstrip() + "..."


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
