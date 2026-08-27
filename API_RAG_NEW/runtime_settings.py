from __future__ import annotations

import os

from dotenv import load_dotenv


load_dotenv()


def parse_cors_origins(raw_value: str | None) -> list[str]:
    if raw_value is None:
        return ["http://localhost:3000", "http://localhost:8080"]

    origins = [item.strip() for item in raw_value.split(",") if item.strip()]
    if "*" in origins:
        raise ValueError("RAG_CORS_ORIGINS must not contain a wildcard origin.")
    return origins


def get_bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    normalized = raw_value.strip().casefold()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


RAG_INTERNAL_API_KEY = os.getenv("RAG_INTERNAL_API_KEY") or None
RAG_REQUIRE_INTERNAL_API_KEY = get_bool_env("RAG_REQUIRE_INTERNAL_API_KEY", True)
