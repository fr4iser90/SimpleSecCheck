"""
Unit tests for ScanService.cancel_scan (load scan, cancel, update DB, notify queue).
"""
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

_BACKEND = Path(__file__).resolve().parent.parent.parent / "backend"
if _BACKEND.exists() and str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from domain.entities.scan import Scan, ScanStatus, ScanType
from application.services.scan_service import ScanService
from application.dtos.request_dto import CancelScanRequestDTO
from domain.exceptions.scan_exceptions import ScanNotFoundException, ScanValidationException


@pytest.fixture
def mock_validation():
    return MagicMock()


@pytest.fixture
def mock_scan_repository():
    return MagicMock()


@pytest.fixture
def mock_queue_service():
    m = MagicMock()
    m.cancel_scan = AsyncMock(return_value=True)
    return m


@pytest.fixture
def mock_result_service():
    return MagicMock()


@pytest.fixture
def scan_service(mock_validation, mock_scan_repository, mock_queue_service, mock_result_service):
    return ScanService(
        mock_validation,
        mock_scan_repository,
        mock_queue_service,
        mock_result_service,
    )


@pytest.mark.asyncio
async def test_cancel_scan_loads_updates_and_signals_queue(scan_service, mock_scan_repository, mock_queue_service):
    """cancel_scan loads scan, calls cancel(), updates repo, calls queue_service.cancel_scan."""
    scan = Scan(
        id="scan-1",
        name="test",
        target_url="https://github.com/foo/bar",
        target_type="git_repo",
        scan_type=ScanType.CODE,
        status=ScanStatus.PENDING,
        user_id="user-1",
    )
    mock_scan_repository.get_by_id = AsyncMock(return_value=scan)
    mock_scan_repository.update = AsyncMock(return_value=scan)

    request = CancelScanRequestDTO(scan_id="scan-1", cancelled_by="user-1")
    result = await scan_service.cancel_scan(request)

    assert result.status == ScanStatus.CANCELLED
    mock_scan_repository.get_by_id.assert_called_once_with("scan-1")
    mock_scan_repository.update.assert_called_once()
    mock_queue_service.cancel_scan.assert_called_once_with("scan-1")


@pytest.mark.asyncio
async def test_cancel_scan_pending_allowed(scan_service, mock_scan_repository):
    """Cancelling a pending scan is allowed."""
    scan = Scan(
        id="s2",
        status=ScanStatus.PENDING,
        target_url="https://x.co",
        target_type="git_repo",
        scan_type=ScanType.CODE,
        user_id="user-1",
    )
    mock_scan_repository.get_by_id = AsyncMock(return_value=scan)
    mock_scan_repository.update = AsyncMock(return_value=scan)

    request = CancelScanRequestDTO(scan_id="s2", cancelled_by="user-1")
    result = await scan_service.cancel_scan(request)
    assert result.status == ScanStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_scan_not_found_raises(scan_service, mock_scan_repository):
    """cancel_scan raises ScanNotFoundException when scan does not exist."""
    mock_scan_repository.get_by_id = AsyncMock(return_value=None)

    request = CancelScanRequestDTO(scan_id="missing")
    with pytest.raises(ScanNotFoundException):
        await scan_service.cancel_scan(request)


@pytest.mark.asyncio
async def test_cancel_scan_invalid_status_raises(scan_service, mock_scan_repository):
    """cancel_scan raises ScanValidationException when scan is already completed."""
    scan = Scan(
        id="s3",
        status=ScanStatus.COMPLETED,
        target_url="https://x.co",
        target_type="git_repo",
        scan_type=ScanType.CODE,
        user_id="user-1",
    )
    mock_scan_repository.get_by_id = AsyncMock(return_value=scan)

    request = CancelScanRequestDTO(scan_id="s3")
    with pytest.raises(ScanValidationException):
        await scan_service.cancel_scan(request)
