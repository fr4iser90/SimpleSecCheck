"""AuthMiddleware must resolve API keys via ActorContextDependency.resolve_context."""
import asyncio
import importlib.util
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Request
from starlette.datastructures import Headers

_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


def _load_auth_middleware():
    spec = importlib.util.spec_from_file_location(
        "auth_middleware",
        _BACKEND / "api" / "middleware" / "auth_middleware.py",
    )
    mod = importlib.util.module_from_spec(spec)
    # Minimal stubs for imports
    mock_settings = type(sys)("config.settings")
    mock_settings.settings = type("S", (), {"ACCESS_MODE": "private"})()
    sys.modules.setdefault("config.settings", mock_settings)

    mock_deps = type(sys)("api.deps.actor_context")

    class ActorContext:
        def __init__(self, **kwargs):
            self.user_id = kwargs.get("user_id")
            self.is_authenticated = kwargs.get("is_authenticated", False)

    class ActorContextDependency:
        async def resolve_context(self, request, response, credentials=None):
            return ActorContext()

        @staticmethod
        def _looks_like_api_key(token):
            return token.startswith("ssc_")

    mock_deps.ActorContext = ActorContext
    mock_deps.ActorContextDependency = ActorContextDependency
    sys.modules.setdefault("api.deps.actor_context", mock_deps)

    spec.loader.exec_module(mod)
    return mod


def test_middleware_uses_resolve_context_for_api_key():
    auth_mod = _load_auth_middleware()
    dep = MagicMock()
    dep.resolve_context = AsyncMock(
        return_value=auth_mod.ActorContext(user_id="u1", is_authenticated=True)
    )
    dep._looks_like_api_key = auth_mod.ActorContextDependency._looks_like_api_key

    middleware = auth_mod.AuthMiddleware(
        MagicMock(),
        actor_context_dependency=dep,
        protected_paths=["/api/v1/resolve-scan"],
    )

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/resolve-scan",
        "headers": [
            (b"authorization", b"Bearer ssc_6243b251_testkey_" + b"x" * 32),
        ],
    }
    request = Request(scope)

    ctx = asyncio.run(
        middleware._resolve_actor_context(request, require_authenticated=True)
    )
    assert ctx.is_authenticated is True
    assert ctx.user_id == "u1"
    dep.resolve_context.assert_awaited_once()


def test_middleware_rejects_invalid_api_key_in_private_mode():
    auth_mod = _load_auth_middleware()
    dep = MagicMock()
    dep.resolve_context = AsyncMock(
        return_value=auth_mod.ActorContext(is_authenticated=False)
    )
    dep._looks_like_api_key = auth_mod.ActorContextDependency._looks_like_api_key

    middleware = auth_mod.AuthMiddleware(
        MagicMock(),
        actor_context_dependency=dep,
        protected_paths=["/api/user/targets"],
    )

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/user/targets",
        "headers": [
            (b"authorization", b"Bearer ssc_deadbeef_" + b"y" * 32),
        ],
    }
    request = Request(scope)

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            middleware._resolve_actor_context(request, require_authenticated=True)
        )
    assert exc.value.status_code == 401
    assert "API key" in str(exc.value.detail)
