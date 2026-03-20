from __future__ import annotations

import re
import uuid
from typing import Any, Sequence


def add_records_to_collection(
    records: Sequence[dict[str, Any]], model: Any, collection: Any
) -> int:
    if not records:
        return 0

    try:
        embeddings = model.encode([record["chunk"] for record in records])
        collection.add(
            ids=[str(uuid.uuid4()) for _ in records],
            embeddings=embeddings,
            metadatas=[dict(record) for record in records],
        )
    except AttributeError as exc:
        if "encode" in str(exc):
            raise RuntimeError(
                "Please configure the embedding model before ingesting data."
            ) from exc
        raise RuntimeError(f"Error saving data to Chroma: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Error saving data to Chroma: {exc}") from exc

    return len(records)


def clean_collection_name(name: str) -> str | None:
    cleaned_name = re.sub(r"[^a-zA-Z0-9_.-]", "", name)
    cleaned_name = re.sub(r"\.{2,}", ".", cleaned_name)
    cleaned_name = re.sub(r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$", "", cleaned_name)
    return cleaned_name[:63] if 3 <= len(cleaned_name) <= 63 else None


def format_retrieved_data(
    metadatas: list[dict[str, Any]], columns_to_answer: Sequence[str]
) -> str:
    lines: list[str] = []

    for index, metadata in enumerate(metadatas, start=1):
        columns = [
            f"{column.capitalize()}: {metadata.get(column)}"
            for column in columns_to_answer
            if column in metadata
        ]
        line = f"{index}) {' '.join(columns)}".rstrip()
        lines.append(line)

    return "\n".join(lines)


def vector_search(
    model: Any,
    query: str,
    collection: Any,
    columns_to_answer: Sequence[str],
    number_docs_retrieval: int,
) -> tuple[list[Any], str]:
    query_embeddings = model.encode([query])
    search_results = collection.query(
        query_embeddings=query_embeddings,
        n_results=number_docs_retrieval,
    )
    metadatas = search_results["metadatas"]
    first_result = metadatas[0] if metadatas else []
    return metadatas, format_retrieved_data(first_result, columns_to_answer)
