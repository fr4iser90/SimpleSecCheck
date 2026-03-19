"""
Auto-Scan Scheduler

Background scheduler that creates scans for:
1. UserGitHubRepo (new repos, initial scan)
2. UserScanTarget with auto_scan.enabled and mode=interval (saved targets)

The actual scan execution is handled by the worker that polls the queue.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from infrastructure.container import (
    get_github_repo_repository,
    get_repo_scan_history_repository,
    get_scan_repository,
    get_scan_target_repository,
)
from domain.services.repo_scan_helper import create_repo_scan
from domain.services.target_scan_helper import create_scan_from_target

logger = logging.getLogger(__name__)


class AutoScanScheduler:
    """
    Scheduler for automatic repository scans.

    This service:
    1. Monitors new repositories with auto_scan_enabled = True
    2. Creates scans after a delay and adds them to the queue
    3. The worker then picks up scans from the queue and executes them
    """

    def __init__(self, delay_seconds: int = 45, check_interval_seconds: int = 30):
        """
        Initialize AutoScanScheduler.

        Args:
            delay_seconds: Delay before creating initial scan (default: 45 seconds)
            check_interval_seconds: How often to check for new repos (default: 30 seconds)
        """
        self.delay_seconds = delay_seconds
        self.check_interval_seconds = check_interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the background scheduler task."""
        if self._running:
            logger.warning("Auto-scan scheduler is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info(
            f"Auto-scan scheduler started (delay: {self.delay_seconds}s, "
            f"check interval: {self.check_interval_seconds}s)"
        )

    async def stop(self):
        """Stop the background scheduler task."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Auto-scan scheduler stopped")

    async def _monitor_loop(self):
        """Background loop to check for new repositories and interval-based saved targets."""
        while self._running:
            try:
                await self._check_and_schedule_initial_scans()
                await self._check_and_schedule_target_scans()
                await asyncio.sleep(self.check_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in auto-scan scheduler: {e}", exc_info=True)
                await asyncio.sleep(10)

    async def _check_and_schedule_initial_scans(self):
        """
        Check for repositories that need initial scans.

        Creates scans and adds them to the queue (worker will execute them).
        """
        try:
            repo_repo = get_github_repo_repository()
            history_repo = get_repo_scan_history_repository()
            scan_repo = get_scan_repository()

            cutoff_time = datetime.utcnow() - timedelta(seconds=self.delay_seconds)
            repos = await repo_repo.list_auto_scan_enabled(created_before=cutoff_time)
            if not repos:
                return

            repo_ids = [r.id for r in repos]
            latest_by_repo = await history_repo.get_latest_by_repo_ids(repo_ids)

            for repo in repos:
                try:
                    if repo.id in latest_by_repo:
                        continue
                    active = await scan_repo.find_active_scan_by_user_and_target(
                        repo.user_id, repo.repo_url
                    )
                    if active:
                        continue

                    logger.info(
                        f"Scheduling initial scan for repo {repo.repo_name} "
                        f"(created {datetime.utcnow() - repo.created_at} ago)"
                    )
                    scan_id = await create_repo_scan(
                        repo_url=repo.repo_url,
                        repo_name=repo.repo_name,
                        branch=repo.branch,
                        user_id=repo.user_id,
                        scanners=repo.scanners,
                        metadata={
                            "trigger": "auto_scan_scheduler",
                            "repo_id": repo.id,
                            "delay_seconds": self.delay_seconds,
                        },
                    )
                    if scan_id:
                        logger.info(
                            f"Scan {scan_id} created and queued for repo {repo.repo_name}"
                        )
                    else:
                        logger.error(f"Failed to create scan for repo {repo.repo_name}")
                except Exception as e:
                    logger.error(
                        f"Error processing repo {repo.id} for initial scan: {e}",
                        exc_info=True,
                    )
        except Exception as e:
            logger.error(f"Error checking for initial scans: {e}", exc_info=True)

    async def _check_and_schedule_target_scans(self):
        """
        Check UserScanTarget with auto_scan.enabled and mode=interval.
        Create scan if interval_seconds elapsed since last scan (or never scanned).
        """
        try:
            target_repo = get_scan_target_repository()
            scan_repo = get_scan_repository()

            targets = await target_repo.list_with_auto_scan_interval()
            for target in targets:
                interval_sec = target.auto_scan.interval_seconds
                if not interval_sec or int(interval_sec) <= 0:
                    continue
                interval_sec = int(interval_sec)

                if await scan_repo.find_active_scan_by_user_and_target(
                    target.user_id, target.source
                ):
                    continue

                last_scan = await scan_repo.find_latest_finished_scan_by_user_and_target(
                    target.user_id, target.source
                )
                last_time = None
                if last_scan:
                    last_time = last_scan.completed_at or last_scan.created_at
                if last_time:
                    lt = last_time.replace(tzinfo=None) if last_time.tzinfo else last_time
                    if (datetime.utcnow() - lt).total_seconds() < interval_sec:
                        continue

                logger.info(
                    f"Scheduling interval scan for target {target.id} "
                    f"({target.type}: {target.source[:50]}), interval={interval_sec}s"
                )
                scan_id = await create_scan_from_target(
                    target,
                    metadata_extra={
                        "trigger": "auto_scan_scheduler",
                        "interval_seconds": interval_sec,
                    },
                    enforcement_mode="full",
                )
                if scan_id:
                    logger.info(f"Scan {scan_id} created for target {target.id}")
                else:
                    logger.error(f"Failed to create scan for target {target.id}")
        except Exception as e:
            logger.error(f"Error checking for target scans: {e}", exc_info=True)
