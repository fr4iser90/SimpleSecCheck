"""Worker scanner refresh must re-sync DB even when scanners already exist."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


@pytest.mark.asyncio
async def test_refresh_scanners_runs_container_sync_when_db_already_populated():
    from worker.api import scanner_api

    fake_rows = [{"name": "Semgrep", "scan_types": ["code"], "priority": 1, "enabled": True}]
    scanner_api._database_adapter = object()
    scanner_api._scanner_cache = None
    scanner_api._cache_timestamp = None

    with patch.object(scanner_api, "_require_database_ready", new_callable=AsyncMock) as ready, patch.object(
        scanner_api, "_refresh_scanners_from_container", new_callable=AsyncMock
    ) as refresh, patch.object(
        scanner_api, "_get_scanners_from_database", new_callable=AsyncMock, return_value=fake_rows
    ) as load_db, patch(
        "worker.infrastructure.worker_result_collection.invalidate_merged_worker_result_collection_cache"
    ):
        result = await scanner_api.refresh_scanners()

    ready.assert_awaited_once()
    refresh.assert_awaited_once()
    load_db.assert_awaited_once()
    assert result == {"status": "ok", "count": 1}
