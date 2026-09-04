from __future__ import annotations

import math
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class EvaluationRecord:
    id: str
    document: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvaluationSearchResult:
    id: str
    document: str
    metadata: dict[str, Any]
    distance: float
    vector_rank: int


class EvaluationVectorStore(Protocol):
    name: str

    def replace(self, records: list[EvaluationRecord]) -> None: ...

    def search(
        self, query_embedding: list[float], limit: int
    ) -> list[EvaluationSearchResult]: ...

    def close(self) -> None: ...


class MemoryVectorStore:
    name = "memory"

    def __init__(self) -> None:
        self._records: list[EvaluationRecord] = []

    def replace(self, records: list[EvaluationRecord]) -> None:
        self._records = list(records)

    def search(
        self, query_embedding: list[float], limit: int
    ) -> list[EvaluationSearchResult]:
        ranked = sorted(
            self._records,
            key=lambda record: (_cosine_distance(query_embedding, record.embedding), record.id),
        )[: max(0, limit)]
        return [
            EvaluationSearchResult(
                id=record.id,
                document=record.document,
                metadata=dict(record.metadata),
                distance=_cosine_distance(query_embedding, record.embedding),
                vector_rank=index,
            )
            for index, record in enumerate(ranked)
        ]

    def close(self) -> None:
        return None


class ChromaVectorStore:
    name = "chroma"

    def __init__(self) -> None:
        import chromadb

        self._client = chromadb.EphemeralClient()
        self._collection_name = f"rag_eval_{uuid.uuid4().hex}"
        self._collection = self._client.create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def replace(self, records: list[EvaluationRecord]) -> None:
        if records:
            self._collection.upsert(
                ids=[record.id for record in records],
                documents=[record.document for record in records],
                embeddings=[record.embedding for record in records],
                metadatas=[record.metadata for record in records],
            )

    def search(
        self, query_embedding: list[float], limit: int
    ) -> list[EvaluationSearchResult]:
        response = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=max(1, limit),
            include=["documents", "metadatas", "distances"],
        )
        ids = response.get("ids", [[]])[0]
        documents = response.get("documents", [[]])[0]
        metadatas = response.get("metadatas", [[]])[0]
        distances = response.get("distances", [[]])[0]
        return [
            EvaluationSearchResult(
                id=str(record_id),
                document=str(documents[index]),
                metadata=dict(metadatas[index] or {}),
                distance=float(distances[index]),
                vector_rank=index,
            )
            for index, record_id in enumerate(ids)
        ]

    def close(self) -> None:
        self._client.delete_collection(self._collection_name)


class PgVectorStore:
    name = "pgvector"

    def __init__(self, dsn: str, dimension: int) -> None:
        import psycopg2

        self._connection = psycopg2.connect(dsn)
        self._dimension = int(dimension)
        self._table = f"rag_eval_{uuid.uuid4().hex}"
        if not re.fullmatch(r"[a-z0-9_]+", self._table):
            raise ValueError("Unsafe evaluation table name.")
        with self._connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cursor.execute(
                f"CREATE TEMP TABLE {self._table} ("
                "id text PRIMARY KEY, document text NOT NULL, metadata jsonb NOT NULL, "
                f"embedding vector({self._dimension}) NOT NULL)"
            )
        self._connection.commit()

    def replace(self, records: list[EvaluationRecord]) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(f"TRUNCATE TABLE {self._table}")
            cursor.executemany(
                f"INSERT INTO {self._table} (id, document, metadata, embedding) "
                "VALUES (%s, %s, %s::jsonb, %s::vector)",
                [
                    (
                        record.id,
                        record.document,
                        _json_dumps(record.metadata),
                        _vector_literal(record.embedding),
                    )
                    for record in records
                ],
            )
        self._connection.commit()

    def search(
        self, query_embedding: list[float], limit: int
    ) -> list[EvaluationSearchResult]:
        vector = _vector_literal(query_embedding)
        with self._connection.cursor() as cursor:
            cursor.execute(
                f"SELECT id, document, metadata, embedding <=> %s::vector AS distance "
                f"FROM {self._table} ORDER BY embedding <=> %s::vector, id LIMIT %s",
                (vector, vector, max(1, limit)),
            )
            rows = cursor.fetchall()
        return [
            EvaluationSearchResult(
                id=str(row[0]),
                document=str(row[1]),
                metadata=dict(row[2]),
                distance=float(row[3]),
                vector_rank=index,
            )
            for index, row in enumerate(rows)
        ]

    def close(self) -> None:
        self._connection.close()


def _cosine_distance(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 1.0
    return 1.0 - (dot / (left_norm * right_norm))


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(format(float(value), ".12g") for value in vector) + "]"


def _json_dumps(value: dict[str, Any]) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True)
