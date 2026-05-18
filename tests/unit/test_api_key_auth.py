"""
Unit tests: API key format, service authentication, and actor context resolution.
"""
import asyncio
import importlib.util
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


def _load_module(name: str, rel_path: str):
    spec = importlib.util.spec_from_file_location(name, _BACKEND / rel_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_api_key_utils = _load_module("api_key_utils", "api/auth/api_key_utils.py")
generate_api_key = _api_key_utils.generate_api_key
hash_api_key = _api_key_utils.hash_api_key
is_api_key_token = _api_key_utils.is_api_key_token

from application.services.api_key_service import ApiKeyService
from domain.entities.api_key import ApiKey
from domain.entities.user import User, UserRole


def test_is_api_key_token():
    assert is_api_key_token("ssc_abc12345_" + "x" * 20)
    assert not is_api_key_token("eyJhbGciOiJIUzI1NiJ9.payload.sig")
    assert not is_api_key_token("ssc_short")
    assert not is_api_key_token("")


def test_hash_api_key_deterministic():
    plain = "ssc_deadbeef_" + "a" * 32
    assert hash_api_key(plain) == hash_api_key(plain)
    assert len(hash_api_key(plain)) == 64


def test_generate_api_key_format():
    uid = "12345678-abcd-efgh-ijkl-123456789012"
    key = generate_api_key(uid)
    assert key.startswith("ssc_12345678_")
    assert is_api_key_token(key)


def test_api_key_service_authenticate_success():
    plain = generate_api_key("user-uuid-1")
    key_hash = hash_api_key(plain)
    api_key = ApiKey(
        id="key-1",
        user_id="user-uuid-1",
        name="test",
        key_hash=key_hash,
        created_at=datetime.utcnow(),
        is_active=True,
    )
    user = User(
        id="user-uuid-1",
        email="u@test.local",
        username="u",
        role=UserRole.USER,
        is_active=True,
    )
    repo = AsyncMock()
    repo.get_by_key_hash = AsyncMock(return_value=api_key)
    repo.touch_last_used = AsyncMock()
    user_repo = AsyncMock()
    user_repo.get_by_id = AsyncMock(return_value=user)

    svc = ApiKeyService(repo, user_repository=user_repo)
    result = asyncio.run(svc.authenticate(key_hash))
    assert result is not None
    got_key, got_user = result
    assert got_key.id == "key-1"
    assert got_user.id == "user-uuid-1"
    repo.touch_last_used.assert_awaited_once_with("key-1")


def test_api_key_service_authenticate_expired():
    key_hash = hash_api_key("ssc_expired_" + "b" * 32)
    api_key = ApiKey(
        id="key-2",
        user_id="user-uuid-1",
        name="old",
        key_hash=key_hash,
        created_at=datetime.utcnow() - timedelta(days=10),
        expires_at=datetime.utcnow() - timedelta(days=1),
        is_active=True,
    )
    repo = AsyncMock()
    repo.get_by_key_hash = AsyncMock(return_value=api_key)
    user_repo = AsyncMock()

    svc = ApiKeyService(repo, user_repository=user_repo)
    assert asyncio.run(svc.authenticate(key_hash)) is None
    user_repo.get_by_id.assert_not_awaited()


def test_looks_like_api_key_helper():
    """ActorContext uses the same prefix rule as api_key_utils."""
    assert is_api_key_token("ssc_" + "a" * 40)
    assert not is_api_key_token("not-a-key")
