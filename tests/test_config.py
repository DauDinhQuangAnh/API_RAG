from __future__ import annotations

import pytest

from API_RAG_NEW.config import PROJECT_ROOT, resolve_chroma_db_path
from API_RAG_NEW.runtime_settings import parse_cors_origins


def test_cors_defaults_are_loopback_only_when_variable_is_absent() -> None:
    assert parse_cors_origins(None) == [
        "http://localhost:3000",
        "http://localhost:8080",
    ]


def test_explicit_empty_cors_value_disables_browser_origins() -> None:
    assert parse_cors_origins("") == []


def test_cors_rejects_wildcard_origin() -> None:
    with pytest.raises(ValueError, match="must not contain a wildcard"):
        parse_cors_origins("*")


def test_relative_chroma_path_is_anchored_to_repository() -> None:
    assert resolve_chroma_db_path("db") == str((PROJECT_ROOT / "db").resolve())


def test_absolute_chroma_path_is_preserved(tmp_path) -> None:
    assert resolve_chroma_db_path(str(tmp_path)) == str(tmp_path.resolve())
