"""
Heartbeat-based recovery for scans stuck in ``running`` (worker lost, no liveness).

- Worker updates ``last_heartbeat_at`` while the scanner container runs.
- Stale threshold: SCAN_HEARTBEAT_STALE_SECONDS (default 180).
- Running rows without heartbeat yet: grace SCAN_HEARTBEAT_NULL_GRACE_SECONDS (default 600).
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import text

from domain.entities.scan import ScanStatus
from infrastructure.database.adapter import db_adapter

logger = logging.getLogger(__name__)


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
    from infrastructure.repositories.scan_repository import DatabaseScanRepository
    from infrastructure.services.queue_service import QueueService

    now = datetime.utcnow()
    stale_cutoff = now - timedelta(seconds=stale_seconds())
    null_cutoff = now - timedelta(seconds=null_grace_seconds())

    await db_adapter.ensure_initialized()
    recovered = 0
    async with db_adapter.async_session() as session:
        result = await session.execute(
            text("""
                SELECT id::text FROM scans
                WHERE status = :running
                AND (
                    (last_heartbeat_at IS NOT NULL AND last_heartbeat_at < :stale_cutoff)
                    OR (
                        last_heartbeat_at IS NULL
                        AND started_at IS NOT NULL
                        AND started_at < :null_cutoff
                    )
                    OR (last_heartbeat_at IS NULL AND started_at IS NULL)
                )
                LIMIT 200
            """),
            {
                "running": ScanStatus.RUNNING.value,
                "stale_cutoff": stale_cutoff,
                "null_cutoff": null_cutoff,
            },
        )
        ids: List[str] = [row[0] for row in result.fetchall()]

    repo = DatabaseScanRepository()
    queue = QueueService()
    patch = json.dumps(
        {
            "heartbeat_recovery": {
                "at": now.isoformat() + "Z",
                "reason": "stale_heartbeat",
            }
        }
    )

    for scan_id in ids:
        async with db_adapter.async_session() as session:
            upd = await session.execute(
                text("""
                    UPDATE scans SET
                        status = :pending,
                        started_at = NULL,
                        last_heartbeat_at = NULL,
                        error_message = NULL,
                        updated_at = :now,
                        retry_count = COALESCE(retry_count, 0) + 1,
                        scan_metadata = COALESCE(scan_metadata::jsonb, '{}'::jsonb) || CAST(:patch AS jsonb)
                    WHERE id = CAST(:sid AS uuid)
                      AND status = :running
                      AND (
                        (last_heartbeat_at IS NOT NULL AND last_heartbeat_at < :stale_cutoff)
                        OR (
                            last_heartbeat_at IS NULL
                            AND started_at IS NOT NULL
                            AND started_at < :null_cutoff
                        )
                        OR (last_heartbeat_at IS NULL AND started_at IS NULL)
                      )
                    RETURNING id
                """),
                {
                    "pending": ScanStatus.PENDING.value,
                    "running": ScanStatus.RUNNING.value,
                    "now": now,
                    "sid": scan_id,
                    "patch": patch,
                    "stale_cutoff": stale_cutoff,
                    "null_cutoff": null_cutoff,
                },
            )
            row = upd.fetchone()
            await session.commit()
            if not row:
                continue
        entity = await repo.get_by_id(scan_id)
        if not entity:
            continue
        try:
            await queue.enqueue_scan(entity)
            recovered += 1
            logger.info(
                "Re-enqueued stale running scan %s (heartbeat recovery)",
                scan_id,
            )
        except Exception as e:
            logger.error("Failed to enqueue recovered scan %s: %s", scan_id, e)
    return recovered
