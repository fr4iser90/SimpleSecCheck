"""
Target Initial Scan Scheduler

After a new target is created, the first scan is not enqueued immediately.
This scheduler runs periodically and enqueues the initial scan for targets
that were created at least initial_scan_delay_seconds ago (admin-configurable).
Targets with initial_scan_paused=True are skipped until the user starts the scan manually.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from infrastructure.container import (
    get_scan_target_repository,
    get_system_state_repository,
)
from domain.services.target_scan_helper import create_scan_from_target
from domain.datetime_serialization import isoformat_utc

logger = logging.getLogger(__name__)

DEFAULT_DELAY_SECONDS = 300
CHECK_INTERVAL_SECONDS = 30


class TargetInitialScanScheduler:
    """
    Scheduler that enqueues the first scan for new targets after a delay.
    Delay is read from SystemState.config.execution_limits.initial_scan_delay_seconds.
    """

    def __init__(self, check_interval_seconds: int = CHECK_INTERVAL_SECONDS):
        self.check_interval_seconds = check_interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        if self._running:
            logger.warning("Target initial-scan scheduler is already running")
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Target initial-scan scheduler started (check every %ss)", self.check_interval_seconds)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Target initial-scan scheduler stopped")

    async def _loop(self):
        while self._running:
            try:
                await self._tick()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Target initial-scan scheduler tick error: %s", e, exc_info=True)
            await asyncio.sleep(self.check_interval_seconds)

    async def _tick(self):
        state_repo = get_system_state_repository()
        state = await state_repo.get_singleton()
        limits = (state.config or {}).get("execution_limits") or {}
        delay_seconds = limits.get("initial_scan_delay_seconds")
        if delay_seconds is None:
            delay_seconds = DEFAULT_DELAY_SECONDS
        else:
            try:
                delay_seconds = int(delay_seconds)
            except (TypeError, ValueError):
                delay_seconds = DEFAULT_DELAY_SECONDS
        if delay_seconds < 0:
            delay_seconds = 0

        cutoff = datetime.utcnow() - timedelta(seconds=delay_seconds)
        target_repo = get_scan_target_repository()
        pending = await target_repo.list_pending_initial_scan(cutoff, limit=50)
        if not pending:
            return

        for target in pending:
            try:
                scan_id = await create_scan_from_target(
                    target,
                    metadata_extra={"trigger": "initial_scan"},
                )
                if scan_id:
                    target.config = dict(target.config or {})
                    target.config["initial_scan_triggered_at"] = isoformat_utc(datetime.utcnow())
                    await target_repo.update(target)
                    logger.info(
                        "Enqueued initial scan %s for target %s (%s)",
                        scan_id[:8],
                        target.id[:8],
                        target.source[:50],
                    )
            except Exception as e:
                logger.warning("Failed to enqueue initial scan for target %s: %s", target.id, e)
