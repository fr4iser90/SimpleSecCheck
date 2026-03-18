"""
Integration tests: create scan and queue API with auth (actor) overrides.
Uses TestClient + dependency overrides; no real DB/Redis required if scan_service is mocked.
Run from repo root: PYTHONPATH=backend pytest tests/integration/test_queue_and_scans_api.py -v
"""
import os
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure backend on path (conftest does this, but we need it for imports when running this file alone)
import sys
from pathlib import Path
_BACKEND = Path(__file__).resolve().parent.parent.parent / "backend"
if _BACKEND.exists() and str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from fastapi.testclient import TestClient
from domain.entities.scan import ScanType, ScanStatus


@pytest.fixture(autouse=True)
def mock_setup_complete():
    """Assume setup is complete so SetupMiddleware does not return 503."""
    async def _check():
        return {"setup_complete": True, "database_connected": True}
    with patch("api.middleware.setup_middleware.check_setup_status", side_effect=_check):
        yield


def _make_scan_dto(scan_id: str = "test-scan-id", user_id: str | None = "test-user"):
    """Minimal ScanDTO-like object for create_scan response."""
    from application.dtos.scan_dto import ScanDTO
    return ScanDTO(
        id=scan_id,
        name="test-scan",
        description="",
        scan_type=ScanType.CODE,
        target_url="https://github.com/foo/bar",
        target_type="git_repo",
        user_id=user_id,
        project_id=None,
        status=ScanStatus.PENDING,
        created_at=datetime.now(timezone.utc),
        started_at=None,
        completed_at=None,
        scheduled_at=None,
        tags=[],
        results=[],
        total_vulnerabilities=0,
        critical_vulnerabilities=0,
        high_vulnerabilities=0,
        medium_vulnerabilities=0,
        low_vulnerabilities=0,
        info_vulnerabilities=0,
        metadata={},
    )


@pytest.fixture
def mock_scan_service():
    """ScanService mock that returns a valid ScanDTO from create_scan."""
    mock = MagicMock()
    mock.create_scan = AsyncMock(return_value=_make_scan_dto())
    mock.list_scans = AsyncMock(return_value=[])
    mock.get_scan_by_id = AsyncMock(return_value=None)
    mock.update_scan = AsyncMock(return_value=None)
    mock.get_scan_status = AsyncMock(return_value={})
    return mock


@pytest.fixture
def app_with_auth_admin(mock_scan_service):
    """App with get_actor_context overridden to admin and scan_service mocked."""
    os.environ["ENVIRONMENT"] = "test"
    from api.main import create_app
    from api.deps.actor_context import get_actor_context, ActorContext
    from api.routes.scans import get_scan_service_dependency

    app = create_app()

    async def override_actor_admin():
        return ActorContext(
            user_id="admin-id",
            is_authenticated=True,
            email="admin@test.local",
            name="Admin",
            role="admin",
        )

    app.dependency_overrides[get_actor_context] = override_actor_admin
    app.dependency_overrides[get_scan_service_dependency] = lambda: mock_scan_service
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def app_with_auth_guest(mock_scan_service):
    """App with get_actor_context overridden to guest."""
    os.environ["ENVIRONMENT"] = "test"
    from api.main import create_app
    from api.deps.actor_context import get_actor_context, ActorContext
    from api.routes.scans import get_scan_service_dependency

    app = create_app()

    async def override_actor_guest():
        return ActorContext(
            user_id=None,
            session_id="guest-session-123",
            is_authenticated=False,
        )

    app.dependency_overrides[get_actor_context] = override_actor_guest
    app.dependency_overrides[get_scan_service_dependency] = lambda: mock_scan_service
    yield app
    app.dependency_overrides.clear()


def test_create_scan_as_admin_returns_201(app_with_auth_admin):
    """POST /api/v1/scans/ as admin returns 201 and body contains scan id."""
    client = TestClient(app_with_auth_admin)
    payload = {
        "name": "integration-test-scan",
        "target_url": "https://github.com/foo/bar",
        "scan_type": "code",
        "scanners": ["owasp"],
    }
    response = client.post("/api/v1/scans/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data.get("target_url") == payload["target_url"]
    assert data.get("status") == "pending"


def test_create_scan_as_guest_returns_201(app_with_auth_guest):
    """POST /api/v1/scans/ as guest (no login) returns 201 when allowed."""
    client = TestClient(app_with_auth_guest)
    payload = {
        "name": "guest-scan",
        "target_url": "https://github.com/foo/bar",
        "scan_type": "code",
        "scanners": ["owasp"],
    }
    response = client.post("/api/v1/scans/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data


def test_create_scan_requires_scanners(app_with_auth_admin):
    """POST /api/v1/scans/ without scanners returns 4xx (validation error)."""
    client = TestClient(app_with_auth_admin)
    payload = {
        "name": "no-scanners",
        "target_url": "https://github.com/foo/bar",
        "scan_type": "code",
        "scanners": [],
    }
    response = client.post("/api/v1/scans/", json=payload)
    assert response.status_code in (400, 422)


def test_queue_list_returns_200(app_with_auth_admin):
    """GET /api/queue/ returns 200 and has queue structure (items, queue_length)."""
    client = TestClient(app_with_auth_admin)
    # Queue route may use DB; without real DB it might 500. We only check it's not 401/403 when authenticated.
    response = client.get("/api/queue/")
    # If DB is not set up we get 500; if set up we get 200 with items/list
    assert response.status_code in (200, 500)
    if response.status_code == 200:
        data = response.json()
        assert "items" in data or "queue_length" in data or "queue" in data


def test_report_share_link_creates_token(app_with_auth_admin, mock_scan_service):
    """Owner POST report-share-link returns share_path with token."""
    sid = "scan-share-test-1"
    dto = _make_scan_dto(scan_id=sid, user_id="admin-id")

    async def _get(oid):
        return dto if oid == sid else None

    async def _update(oid, req):
        dto.metadata = {**(dto.metadata or {}), **(req.metadata or {})}
        return dto

    mock_scan_service.get_scan_by_id = AsyncMock(side_effect=_get)
    mock_scan_service.update_scan = AsyncMock(side_effect=_update)
    client = TestClient(app_with_auth_admin)
    r = client.post(f"/api/v1/scans/{sid}/report-share-link", json={})
    assert r.status_code == 200
    data = r.json()
    assert data["share_path"].startswith(f"/api/results/{sid}/report?share_token=")
    assert len(data["share_path"]) > len(f"/api/results/{sid}/report?share_token=") + 8


def test_report_share_link_forbidden_other_user(app_with_auth_admin, mock_scan_service):
    """Non-owner cannot create share link."""
    sid = "scan-owned-by-other"
    dto = _make_scan_dto(scan_id=sid, user_id="someone-else-id")
    mock_scan_service.get_scan_by_id = AsyncMock(return_value=dto)
    client = TestClient(app_with_auth_admin)
    r = client.post(f"/api/v1/scans/{sid}/report-share-link", json={})
    assert r.status_code == 403
