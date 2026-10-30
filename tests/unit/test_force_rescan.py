"""
Force rescan: skips completed-scan reuse, still joins an in-flight scan.
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from application.dtos.request_dto import ScanRequestDTO
from application.helpers import commit_scan_cache as cache
from application.helpers import scan_dedupe
from application.services import scan_target_service as ts_module
from application.services.scan_service import ScanService
from domain.entities.scan import Scan, ScanStatus, ScanType

USER = "11111111-1111-1111-1111-111111111111"
TARGET = "https://github.com/acme/app"
COMMIT = "abcdef0123456789abcdef0123456789abcdef01"


def _scan(scan_id: str, status: ScanStatus) -> Scan:
    return Scan(
        id=scan_id,
        name="scan",
        target_url=TARGET,
        target_type="git_repo",
        scan_type=ScanType.CODE,
        status=status,
        user_id=USER,
    )


def _request() -> ScanRequestDTO:
    return ScanRequestDTO(name="scan", target_url=TARGET, user_id=USER)


@pytest.fixture
def service():
    return ScanService(MagicMock(), MagicMock(), MagicMock(), MagicMock())


@pytest.fixture
def cache_hit(monkeypatch):
    """Git target on a known commit, with a completed scan whose results are on disk."""
    monkeypatch.setattr(cache, "is_git_repo_scan_request", lambda **kwargs: True)
    monkeypatch.setattr(
        cache,
        "resolve_commit_for_git_request",
        lambda **kwargs: (COMMIT, {"commit_hash": COMMIT}),
    )
    monkeypatch.setattr(cache, "find_active_scan_for_target", AsyncMock(return_value=None))
    monkeypatch.setattr(cache, "find_reusable_completed_for_target", AsyncMock(return_value=None))
    by_commit = AsyncMock(return_value=_scan("cached-scan", ScanStatus.COMPLETED))
    monkeypatch.setattr(cache, "find_reusable_scan_for_commit", by_commit)
    return by_commit


@pytest.mark.asyncio
async def test_completed_scan_reused_when_not_forced(service, cache_hit):
    dto = await service._try_reuse_git_commit_scan(_request())
    assert str(dto.id) == "cached-scan"
    assert dto.metadata.get("commit_cache_hit") is True


@pytest.mark.asyncio
async def test_force_skips_completed_scan_reuse(service, cache_hit):
    assert await service._try_reuse_git_commit_scan(_request(), force=True) is None
    cache_hit.assert_not_awaited()


@pytest.mark.asyncio
async def test_force_still_joins_in_flight_scan(service, monkeypatch):
    monkeypatch.setattr(cache, "is_git_repo_scan_request", lambda **kwargs: True)
    monkeypatch.setattr(
        cache,
        "resolve_commit_for_git_request",
        lambda **kwargs: (COMMIT, {"commit_hash": COMMIT}),
    )
    monkeypatch.setattr(
        cache, "find_active_scan_for_target", AsyncMock(return_value=_scan("live-scan", ScanStatus.RUNNING))
    )
    monkeypatch.setattr(
        scan_dedupe, "collapse_active_duplicates_for_target", AsyncMock(return_value=None)
    )

    dto = await service._try_reuse_git_commit_scan(_request(), force=True)
    assert str(dto.id) == "live-scan"


@pytest.mark.asyncio
async def test_force_skips_latest_completed_when_commit_unresolved(service, monkeypatch):
    monkeypatch.setattr(cache, "is_git_repo_scan_request", lambda **kwargs: True)
    monkeypatch.setattr(cache, "resolve_commit_for_git_request", lambda **kwargs: (None, {}))
    latest = AsyncMock(return_value=_scan("older-scan", ScanStatus.COMPLETED))
    monkeypatch.setattr(cache, "find_reusable_completed_for_target", latest)
    monkeypatch.setattr(cache, "find_active_scan_for_target", AsyncMock(return_value=None))

    assert await service._try_reuse_git_commit_scan(_request(), force=True) is None
    latest.assert_not_awaited()


@pytest.mark.asyncio
async def test_target_service_forwards_force_to_scan_creation(monkeypatch):
    captured = {}

    async def fake_create(target, **kwargs):
        captured.update(kwargs)
        return "new-scan"

    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=MagicMock(id="target-1"))
    monkeypatch.setattr(ts_module, "create_scan_from_target", fake_create)

    svc = ts_module.ScanTargetService(repo)
    assert await svc.trigger_scan("target-1", USER, force=True) == "new-scan"
    assert captured["force"] is True

    assert await svc.trigger_scan("target-1", USER) == "new-scan"
    assert captured["force"] is False
