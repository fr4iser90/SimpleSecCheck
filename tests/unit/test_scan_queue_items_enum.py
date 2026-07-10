"""Regression: get_queue_items must not use ILIKE on PostgreSQL scan_status_enum."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from domain.entities.scan import Scan, ScanStatus, ScanType
from infrastructure.repositories.scan_repository import DatabaseScanRepository


@pytest.mark.asyncio
async def test_get_queue_items_pending_uses_enum_equality_not_ilike():
    repo = DatabaseScanRepository()
    pending_scan = Scan(
        id=str(uuid4()),
        name="test",
        target_url="https://example.com",
        target_type="website",
        scan_type=ScanType.SECURITY,
        status=ScanStatus.PENDING,
        scanners=["trivy"],
        config={},
        user_id=str(uuid4()),
    )

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)

    with patch.object(repo.db_adapter, "ensure_initialized", new_callable=AsyncMock), patch.object(
        repo.db_adapter, "async_session", return_value=mock_ctx
    ), patch.object(repo, "_model_to_entity", new_callable=AsyncMock, return_value=pending_scan):
        items = await repo.get_queue_items(status_filter="pending", limit=10, offset=0)

    assert items == [pending_scan]
    compiled = str(mock_session.execute.await_args.args[0])
    assert "ILIKE" not in compiled.upper()
    assert "scan_status_enum" in compiled or "status" in compiled.lower()
