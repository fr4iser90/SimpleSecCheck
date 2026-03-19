"""
Heartbeat-based recovery for scans stuck in ``running`` (worker lost, no liveness).

- Worker updates ``last_heartbeat_at`` while the scanner container runs.
- Stale threshold: SCAN_HEARTBEAT_STALE_SECONDS (default 180).
- Running rows without heartbeat yet: grace SCAN_HEARTBEAT_NULL_GRACE_SECONDS (default 600).
Uses ScanRepository (DDD).
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional

from domain.entities.scan import ScanStatus
from domain.datetime_serialization import isoformat_utc

logger = logging.getLogger(__name__)


def _get_scan_repository():
    from infrastructure.container import get_scan_repository
    return get_scan_repository()


def _get_queue_service():
    from infrastructure.services.queue_service import QueueService
    return QueueService()


def stale_seconds() -> int:
    return max(60, int(os.getenv("SCAN_HEARTBEAT_STALE_SECONDS", "180")))


def null_grace_seconds() -> int:
    return max(120, int(os.getenv("SCAN_HEARTBEAT_NULL_GRACE_SECONDS", "600")))


def scan_running_is_stale(
    *,
    last_heartbeat_at: Optional[datetime],
    started_at: Optional[datetime],
    now: Optional[datetime] = None,
) -> bool:
    now = now or datetime.utcnow()
    stale_cutoff = now - timedelta(seconds=stale_seconds())
    null_cutoff = now - timedelta(seconds=null_grace_seconds())
    if last_heartbeat_at is not None:
        return last_heartbeat_at < stale_cutoff
    if started_at is not None:
        return started_at < null_cutoff
    return True


async def recover_stale_running_scans() -> int:
    """
    Find running scans with stale/missing heartbeat, set pending + bump retry metadata.
    Returns number of scans re-enqueued.
    """
    now = datetime.utcnow()
    stale_cutoff = now - timedelta(seconds=stale_seconds())
    null_cutoff = now - timedelta(seconds=null_grace_seconds())
    repo = _get_scan_repository()
    queue = _get_queue_service()
    ids: List[str] = await repo.get_stale_running_scan_ids(stale_cutoff, null_cutoff, limit=200)
    recovered = 0
    for scan_id in ids:
        entity = await repo.get_by_id(scan_id)
        if not entity or entity.status != ScanStatus.RUNNING:
            continue
        if not scan_running_is_stale(
            last_heartbeat_at=entity.last_heartbeat_at,
            started_at=entity.started_at,
            now=now,
        ):
            continue
        entity.status = ScanStatus.PENDING
        entity.started_at = None
        entity.last_heartbeat_at = None
        entity.error_message = None
        entity.updated_at = now
        entity.retry_count = (entity.retry_count or 0) + 1
        entity.scan_metadata = {
            **(entity.scan_metadata or {}),
            "heartbeat_recovery": {
                "at": isoformat_utc(now),
                "reason": "stale_heartbeat",
            },
        }
        await repo.update(entity)
        try:
            await queue.enqueue_scan(entity)
            recovered += 1
            logger.info("Re-enqueued stale running scan %s (heartbeat recovery)", scan_id)
        except Exception as e:
            logger.error("Failed to enqueue recovered scan %s: %s", scan_id, e)
    return recovered
