"""Unit tests for target history/findings routes and helpers."""
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

_BACKEND = Path(__file__).resolve().parent.parent.parent / "backend"
if _BACKEND.exists() and str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from domain.entities.scan import Scan, ScanStatus, ScanType
from application.helpers.target_scan_history import scan_to_target_history_entry


def _scan(**kwargs):
    defaults = dict(
        id="scan-1",
        name="s1",
        description="",
        scan_type=ScanType.CODE,
        target_url="https://github.com/org/repo",
        target_type="git_repo",
        user_id="user-1",
        project_id=None,
        status=ScanStatus.COMPLETED,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        started_at=None,
        completed_at=datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc),
        scheduled_at=None,
        tags=[],
        results=[],
        total_vulnerabilities=5,
        critical_vulnerabilities=1,
        high_vulnerabilities=2,
        medium_vulnerabilities=1,
        low_vulnerabilities=1,
        info_vulnerabilities=0,
        scan_metadata={"commit_hash": "abc123"},
        config={"git_branch": "main"},
    )
    defaults.update(kwargs)
    return Scan(**defaults)


def test_scan_to_target_history_entry():
    entry = scan_to_target_history_entry(_scan())
    assert entry["scan_id"] == "scan-1"
    assert entry["status"] == "completed"
    assert entry["branch"] == "main"
    assert entry["commit_hash"] == "abc123"
    assert entry["vulnerabilities"]["total"] == 5
    assert entry["vulnerabilities"]["critical"] == 1


@pytest.fixture
def mock_setup_complete():
    from unittest.mock import patch

    async def _check():
        return {"setup_complete": True, "database_connected": True}

    with patch("api.middleware.setup_middleware.check_setup_status", side_effect=_check):
        yield


@pytest.fixture
def app_with_user_auth(mock_setup_complete):
    import os
    from api.main import create_app
    from api.deps.actor_context import get_authenticated_user, ActorContext
    from api.routes.user import (
        get_scan_target_service_dependency,
        get_scan_repository_dependency,
        get_scan_service_dependency,
    )

    os.environ["ENVIRONMENT"] = "test"
    app = create_app()

    target = MagicMock()
    target.id = "target-1"
    target.source = "https://github.com/org/repo"
    target.user_id = "user-1"

    target_svc = MagicMock()
    target_svc.get_by_id = AsyncMock(return_value=target)

    scan = _scan()
    repo = MagicMock()
    repo.get_target_scan_history_page = AsyncMock(return_value=([scan], 1))
    repo.find_latest_finished_scan_by_user_and_target = AsyncMock(return_value=scan)
    repo.get_by_id = AsyncMock(return_value=scan)

    scan_svc = MagicMock()
    from application.dtos.scan_dto import ScanDTO

    scan_svc.get_scan_by_id = AsyncMock(
        return_value=ScanDTO.from_entity(scan)
    )

    async def override_user():
        return ActorContext(
            user_id="user-1",
            is_authenticated=True,
            email="u@test.local",
            name="User",
            role="user",
        )

    app.dependency_overrides[get_authenticated_user] = override_user
    app.dependency_overrides[get_scan_target_service_dependency] = lambda: target_svc
    app.dependency_overrides[get_scan_repository_dependency] = lambda: repo
    app.dependency_overrides[get_scan_service_dependency] = lambda: scan_svc
    yield app, repo, scan_svc
    app.dependency_overrides.clear()


def test_get_target_history(app_with_user_auth):
    from fastapi.testclient import TestClient

    app, repo, _ = app_with_user_auth
    client = TestClient(app)
    resp = client.get("/api/user/targets/target-1/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["target_id"] == "target-1"
    assert data["total"] == 1
    assert len(data["entries"]) == 1
    assert data["entries"][0]["scan_id"] == "scan-1"
    repo.get_target_scan_history_page.assert_awaited_once()


def test_get_target_findings_uses_latest_scan(app_with_user_auth, monkeypatch):
    from fastapi.testclient import TestClient
    from api.schemas.scan_schemas import (
        ScanFindingsResponseSchema,
        ScanFindingsSummarySchema,
    )

    app, repo, scan_svc = app_with_user_auth

    async def fake_findings(*args, **kwargs):
        return ScanFindingsResponseSchema(
            scan_id="scan-1",
            status="completed",
            generated_at=None,
            source="file",
            summary=ScanFindingsSummarySchema(
                total_vulnerabilities=1,
                critical_vulnerabilities=0,
                high_vulnerabilities=1,
                medium_vulnerabilities=0,
                low_vulnerabilities=0,
                info_vulnerabilities=0,
            ),
            findings=[],
            pagination=None,
        )

    monkeypatch.setattr(
        "application.helpers.scan_findings_handler.get_scan_findings_response",
        fake_findings,
    )

    client = TestClient(app)
    resp = client.get("/api/user/targets/target-1/findings?limit=10")
    assert resp.status_code == 200
    assert resp.json()["scan_id"] == "scan-1"
    repo.find_latest_finished_scan_by_user_and_target.assert_awaited_once()
