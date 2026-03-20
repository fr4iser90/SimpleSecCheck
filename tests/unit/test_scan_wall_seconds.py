"""max_scan_wall_seconds derived from tool timeouts + overhead, capped by admin."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from application.services.scan_enforcement import resolve_max_scan_wall_seconds_for_scan
from domain.entities.scan import Scan, ScanType
from domain.entities.scanner import Scanner


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_wall_seconds_sums_selected_tools_and_overhead() -> None:
    now = _utc_now()
    trivy = Scanner(
        id="1",
        name="Trivy",
        scan_types=["code"],
        priority=1,
        requires_condition=None,
        enabled=True,
        scanner_metadata={"tools_key": "trivy"},
        created_at=now,
        updated_at=now,
    )
    repo = AsyncMock()
    repo.list_all = AsyncMock(return_value=[trivy])
    scan = Scan(
        scanners=["Trivy"],
        scan_type=ScanType.CODE,
        config={},
        created_at=now,
        updated_at=now,
    )
    merged = {
        "trivy": {"timeout": 400, "enabled": True, "env": {}, "config": {}, "tools_key": "trivy"}
    }
    with patch(
        "infrastructure.container.get_scanner_repository", return_value=repo
    ), patch(
        "application.services.scan_enforcement._load_limits_and_policies",
        return_value=({}, {}),
    ):
        w = await resolve_max_scan_wall_seconds_for_scan(scan, merged)
    assert w == 180 + 400


@pytest.mark.asyncio
async def test_wall_seconds_respects_admin_max_scan_duration() -> None:
    now = _utc_now()
    trivy = Scanner(
        id="1",
        name="Trivy",
        scan_types=["code"],
        priority=1,
        requires_condition=None,
        enabled=True,
        scanner_metadata={"tools_key": "trivy"},
        created_at=now,
        updated_at=now,
    )
    repo = AsyncMock()
    repo.list_all = AsyncMock(return_value=[trivy])
    scan = Scan(
        scanners=["Trivy"],
        scan_type=ScanType.CODE,
        config={},
        created_at=now,
        updated_at=now,
    )
    merged = {"trivy": {"timeout": 9000, "enabled": True, "env": {}, "config": {}, "tools_key": "trivy"}}
    limits = {"max_scan_duration_seconds": 600}
    with patch(
        "infrastructure.container.get_scanner_repository", return_value=repo
    ), patch(
        "application.services.scan_enforcement._load_limits_and_policies",
        return_value=(limits, {}),
    ):
        w = await resolve_max_scan_wall_seconds_for_scan(scan, merged)
    assert w == 600
