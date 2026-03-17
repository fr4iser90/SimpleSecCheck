"""
Unit tests for QueueService (FIFO, priority, round_robin strategies).
Mocks Redis and get_settings; no server or real Redis required.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from domain.entities.scan import Scan, ScanType, ScanStatus
from infrastructure.services.queue_service import QueueService


def _make_scan(
    scan_id: str = "scan-123",
    priority: int = 0,
    user_id: str | None = None,
    scan_metadata: dict | None = None,
) -> Scan:
    return Scan(
        id=scan_id,
        name="test-scan",
        target_url="https://github.com/foo/bar",
        target_type="git_repo",
        scan_type=ScanType.CODE,
        status=ScanStatus.PENDING,
        scanners=["owasp"],
        config={},
        user_id=user_id,
        scan_metadata=scan_metadata or {},
        priority=priority,
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def mock_redis():
    """Mock Redis client (async methods)."""
    m = MagicMock()
    m.is_connected = True
    m.connect = AsyncMock()
    m.lpush = AsyncMock(return_value=1)
    m.set = AsyncMock()
    m.zadd = AsyncMock(return_value=1)
    m.lrange = AsyncMock(return_value=[])
    m.lrem = AsyncMock(return_value=1)
    m.zrem = AsyncMock(return_value=1)
    m.delete = AsyncMock()
    m.zcard = AsyncMock(return_value=0)
    m.redis = MagicMock()
    m.redis.llen = AsyncMock(return_value=0)
    return m


@pytest.mark.asyncio
async def test_enqueue_fifo_uses_list(mock_redis):
    """FIFO strategy: enqueue should LPUSH to scan_queue list."""
    with patch("infrastructure.services.queue_service.redis_client", mock_redis), \
         patch("infrastructure.services.queue_service.get_settings") as mock_settings:
        mock_settings.return_value.QUEUE_STRATEGY = "fifo"
        svc = QueueService()
        scan = _make_scan("s1")
        await svc.enqueue_scan(scan)
        mock_redis.lpush.assert_called_once()
        call_args = mock_redis.lpush.call_args
        assert call_args[0][0] == QueueService.QUEUE_KEY
        import json
        payload = json.loads(call_args[0][1])
        assert payload["scan_id"] == "s1"
        assert payload["target_url"] == scan.target_url
        mock_redis.zadd.assert_not_called()
        mock_redis.set.assert_not_called()


@pytest.mark.asyncio
async def test_enqueue_priority_uses_sorted_set_and_scan_key(mock_redis):
    """Priority strategy: enqueue should ZADD and SET scan:{id}."""
    with patch("infrastructure.services.queue_service.redis_client", mock_redis), \
         patch("infrastructure.services.queue_service.get_settings") as mock_settings:
        mock_settings.return_value.QUEUE_STRATEGY = "priority"
        svc = QueueService()
        scan = _make_scan("s-priority", priority=10)
        await svc.enqueue_scan(scan)
        mock_redis.set.assert_called_once()
        set_key = mock_redis.set.call_args[0][0]
        set_val = mock_redis.set.call_args[0][1]
        assert set_key == "scan:s-priority"
        assert "s-priority" in set_val
        mock_redis.zadd.assert_called_once()
        zkey, zmapping = mock_redis.zadd.call_args[0][0], mock_redis.zadd.call_args[0][1]
        assert zkey == QueueService.QUEUE_PRIORITY_KEY
        assert "s-priority" in zmapping
        # lower score = earlier (higher priority first): (1000-10)*1e10 + ts
        assert zmapping["s-priority"] >= (1000 - 10) * 1e10
        mock_redis.lpush.assert_not_called()


@pytest.mark.asyncio
async def test_enqueue_round_robin_uses_list(mock_redis):
    """Round-robin strategy: same as FIFO, uses list."""
    with patch("infrastructure.services.queue_service.redis_client", mock_redis), \
         patch("infrastructure.services.queue_service.get_settings") as mock_settings:
        mock_settings.return_value.QUEUE_STRATEGY = "round_robin"
        svc = QueueService()
        scan = _make_scan("s-rr", user_id="user-1")
        await svc.enqueue_scan(scan)
        mock_redis.lpush.assert_called_once()
        mock_redis.zadd.assert_not_called()


@pytest.mark.asyncio
async def test_remove_scan_from_queue_fifo(mock_redis):
    """remove_scan_from_queue with FIFO: LREM from list."""
    with patch("infrastructure.services.queue_service.redis_client", mock_redis), \
         patch("infrastructure.services.queue_service.get_settings") as mock_settings:
        mock_settings.return_value.QUEUE_STRATEGY = "fifo"
        mock_redis.lrange = AsyncMock(return_value=[
            '{"scan_id": "other"}',
            '{"scan_id": "to-remove"}',
        ])
        svc = QueueService()
        removed = await svc.remove_scan_from_queue("to-remove")
        assert removed is True
        mock_redis.lrem.assert_called_once()
        mock_redis.zrem.assert_not_called()


@pytest.mark.asyncio
async def test_remove_scan_from_queue_priority(mock_redis):
    """remove_scan_from_queue with priority: ZREM and delete scan:{id}."""
    with patch("infrastructure.services.queue_service.redis_client", mock_redis), \
         patch("infrastructure.services.queue_service.get_settings") as mock_settings:
        mock_settings.return_value.QUEUE_STRATEGY = "priority"
        mock_redis.zrem = AsyncMock(return_value=1)
        svc = QueueService()
        removed = await svc.remove_scan_from_queue("scan-1")
        assert removed is True
        mock_redis.zrem.assert_called_once_with(QueueService.QUEUE_PRIORITY_KEY, "scan-1")
        mock_redis.delete.assert_called_once_with("scan:scan-1")


@pytest.mark.asyncio
async def test_get_queue_length_fifo(mock_redis):
    """get_queue_length with FIFO uses LLEN."""
    with patch("infrastructure.services.queue_service.redis_client", mock_redis), \
         patch("infrastructure.services.queue_service.get_settings") as mock_settings:
        mock_settings.return_value.QUEUE_STRATEGY = "fifo"
        mock_redis.redis.llen = AsyncMock(return_value=5)
        svc = QueueService()
        length = await svc.get_queue_length()
        assert length == 5


@pytest.mark.asyncio
async def test_get_queue_length_priority(mock_redis):
    """get_queue_length with priority uses ZCARD."""
    with patch("infrastructure.services.queue_service.redis_client", mock_redis), \
         patch("infrastructure.services.queue_service.get_settings") as mock_settings:
        mock_settings.return_value.QUEUE_STRATEGY = "priority"
        mock_redis.zcard = AsyncMock(return_value=3)
        svc = QueueService()
        length = await svc.get_queue_length()
        assert length == 3
