from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from API_RAG_NEW import security


def test_missing_key_fails_closed_when_internal_auth_is_required() -> None:
    with (
        patch.object(security, "RAG_INTERNAL_API_KEY", None),
        patch.object(security, "RAG_REQUIRE_INTERNAL_API_KEY", True),
        pytest.raises(HTTPException) as exc_info,
    ):
        security.require_internal_api_key(None)

    assert exc_info.value.status_code == 503


def test_missing_or_wrong_request_key_is_rejected() -> None:
    with (
        patch.object(security, "RAG_INTERNAL_API_KEY", "expected-secret"),
        patch.object(security, "RAG_REQUIRE_INTERNAL_API_KEY", True),
    ):
        with pytest.raises(HTTPException) as missing_exc:
            security.require_internal_api_key(None)
        with pytest.raises(HTTPException) as wrong_exc:
            security.require_internal_api_key("wrong-secret")

    assert missing_exc.value.status_code == 401
    assert wrong_exc.value.status_code == 401


def test_matching_request_key_is_accepted() -> None:
    with (
        patch.object(security, "RAG_INTERNAL_API_KEY", "expected-secret"),
        patch.object(security, "RAG_REQUIRE_INTERNAL_API_KEY", True),
    ):
        assert security.require_internal_api_key("expected-secret") is None


def test_explicit_local_opt_out_remains_available() -> None:
    with (
        patch.object(security, "RAG_INTERNAL_API_KEY", None),
        patch.object(security, "RAG_REQUIRE_INTERNAL_API_KEY", False),
    ):
        assert security.require_internal_api_key(None) is None
