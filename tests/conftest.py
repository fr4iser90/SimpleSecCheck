"""
Pytest configuration and shared fixtures
"""
import os
import sys
from pathlib import Path

import pytest

# Ensure backend is on path when running tests from repo root
_BACKEND = Path(__file__).resolve().parent.parent / "backend"
if _BACKEND.exists() and str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# Required by backend config (no defaults in code); set before any backend import
for _key in ("JWT_SECRET_KEY", "SECRET_KEY", "SESSION_SECRET"):
    if _key not in os.environ:
        os.environ[_key] = "test-secret-do-not-use-in-production-min-32-chars"

# Backend POSTGRES_PASSWORD has no default
if "POSTGRES_PASSWORD" not in os.environ:
    os.environ["POSTGRES_PASSWORD"] = "ci-only-postgres-placeholder-not-for-production"

def pytest_addoption(parser):
    """Add custom pytest options."""
    parser.addoption(
        "--cleanup",
        action="store_true",
        default=False,
        help="Clean up Docker volumes after tests (docker compose down -v)"
    )
    parser.addoption(
        "--no-cleanup",
        action="store_true",
        default=False,
        help="Skip cleanup (keep containers and volumes)"
    )


# ----- Integration fixtures: app, client, auth overrides -----

@pytest.fixture
def app():
    """FastAPI app for integration tests (no live server)."""
    os.environ["ENVIRONMENT"] = "test"
    from api.main import create_app
    return create_app()


@pytest.fixture
def client(app):
    """Starlette TestClient (sync) for integration tests."""
    from starlette.testclient import TestClient
    return TestClient(app)


@pytest.fixture
def actor_context_admin():
    """ActorContext for an authenticated admin user."""
    from api.deps.actor_context import ActorContext
    return ActorContext(
        user_id="test-admin-id",
        is_authenticated=True,
        email="admin@test.local",
        name="Admin",
        role="admin",
    )


@pytest.fixture
def actor_context_user():
    """ActorContext for an authenticated non-admin user."""
    from api.deps.actor_context import ActorContext
    return ActorContext(
        user_id="test-user-id",
        is_authenticated=True,
        email="user@test.local",
        name="User",
        role="user",
    )


@pytest.fixture
def actor_context_guest():
    """ActorContext for a guest (no login)."""
    from api.deps.actor_context import ActorContext
    return ActorContext(
        user_id=None,
        session_id="test-session-123",
        is_authenticated=False,
    )
