from __future__ import annotations

import json
import logging
import re
import threading
import time
import uuid
from collections import Counter
from contextvars import ContextVar
from typing import Any

from fastapi import Request


_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_safe_id = re.compile(r"^[a-zA-Z0-9._:-]{1,128}$")
_uuid_path = re.compile(r"/[0-9a-f]{8}-[0-9a-f-]{27,}", re.IGNORECASE)
_number_path = re.compile(r"/\d+(?=/|$)")
_counters: Counter[tuple[str, tuple[tuple[str, str], ...]]] = Counter()
_lock = threading.Lock()


def normalize_correlation_id(value: str | None) -> str:
    candidate = str(value or "").strip()
    return candidate if _safe_id.fullmatch(candidate) else str(uuid.uuid4())


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def increment(name: str, **labels: Any) -> None:
    label_tuple = tuple(sorted((key, str(value)) for key, value in labels.items()))
    with _lock:
        _counters[(name, label_tuple)] += 1


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def render_metrics() -> str:
    lines = [
        "# HELP weavecarbon_rag_process_uptime_seconds Process uptime in seconds.",
        "# TYPE weavecarbon_rag_process_uptime_seconds gauge",
        f"weavecarbon_rag_process_uptime_seconds {time.monotonic():.3f}",
    ]
    with _lock:
        snapshot = sorted(_counters.items())
    for (name, labels), value in snapshot:
        suffix = ""
        if labels:
            suffix = "{" + ",".join(
                f'{key}="{_escape(label_value)}"' for key, label_value in labels
            ) + "}"
        lines.append(f"{name}{suffix} {value}")
    return "\n".join(lines) + "\n"


def reset_metrics_for_tests() -> None:
    with _lock:
        _counters.clear()


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname.lower(),
            "message": record.getMessage(),
            "correlation_id": get_correlation_id(),
        }
        return json.dumps(payload, ensure_ascii=False)


logger = logging.getLogger("weavecarbon.rag")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False


async def operational_middleware(request: Request, call_next):
    correlation_id = normalize_correlation_id(request.headers.get("x-correlation-id"))
    token = _correlation_id.set(correlation_id)
    started_at = time.perf_counter()
    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = (time.perf_counter() - started_at) * 1000
        response_status = locals().get("response")
        status_code = getattr(response_status, "status_code", 500)
        safe_path = _number_path.sub("/:id", _uuid_path.sub("/:id", request.url.path))
        increment(
            "weavecarbon_rag_http_requests_total",
            method=request.method,
            path=safe_path,
            status=status_code,
        )
        logger.info(
            "request_completed method=%s path=%s status=%s duration_ms=%.1f",
            request.method,
            safe_path,
            status_code,
            duration_ms,
        )
        if response_status is not None:
            response_status.headers["X-Correlation-ID"] = correlation_id
        _correlation_id.reset(token)
