"""
Auto-Scan Scheduler

Background scheduler that creates scans for new repositories and adds them to the queue.
The actual scan execution is handled by the worker that polls the queue.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, and_

from infrastructure.database.adapter import db_adapter
from infrastructure.database.models import UserGitHubRepo, RepoScanHistory
from domain.services.repo_scan_helper import create_repo_scan

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
        logger.info(f"Auto-scan scheduler started (delay: {self.delay_seconds}s, check interval: {self.check_interval_seconds}s)")
    
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
        """Background loop to check for new repositories that need scans."""
        while self._running:
            try:
                await self._check_and_schedule_initial_scans()
                await asyncio.sleep(self.check_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in auto-scan scheduler: {e}", exc_info=True)
                await asyncio.sleep(10)  # Wait 10 seconds before retrying on error
    
    async def _check_and_schedule_initial_scans(self):
        """
        Check for repositories that need initial scans.
        
        Creates scans and adds them to the queue (worker will execute them).
        """
        try:
            async with db_adapter.async_session() as session:
                # Find repos that:
                # 1. Have auto_scan_enabled = True
                # 2. Were created more than delay_seconds ago
                # 3. Have no scan history (never scanned)
                
                cutoff_time = datetime.utcnow() - timedelta(seconds=self.delay_seconds)
                
                # Get all repos with auto-scan enabled
                repos_result = await session.execute(
                    select(UserGitHubRepo).where(
                        UserGitHubRepo.auto_scan_enabled == True,
                        UserGitHubRepo.created_at <= cutoff_time
                    )
                )
                repos = repos_result.scalars().all()
                
                if not repos:
                    return
                
                # Check each repo for scan history
                for repo in repos:
                    try:
                        # Check if repo has any scan history
                        history_result = await session.execute(
                            select(RepoScanHistory)
                            .where(RepoScanHistory.repo_id == repo.id)
                            .limit(1)
                        )
                        has_history = history_result.scalar_one_or_none() is not None
                        
                        if not has_history:
                            # Check if there's already a pending/running scan for this repo
                            from infrastructure.database.models import Scan
                            active_scan_result = await session.execute(
                                select(Scan).where(
                                    and_(
                                        Scan.user_id == repo.user_id,
                                        Scan.status.in_(["pending", "running"]),
                                        Scan.target_url.contains(repo.repo_url)
                                    )
                                ).limit(1)
                            )
                            active_scan = active_scan_result.scalar_one_or_none()
                            
                            if not active_scan:
                                # Create scan and add to queue (worker will execute it)
                                logger.info(f"Scheduling initial scan for repo {repo.repo_name} (created {datetime.utcnow() - repo.created_at} ago)")
                                
                                scan_id = await create_repo_scan(
                                    repo_url=repo.repo_url,
                                    repo_name=repo.repo_name,
                                    branch=repo.branch,
                                    user_id=str(repo.user_id),
                                    metadata={
                                        "trigger": "auto_scan_scheduler",
                                        "repo_id": str(repo.id),
                                        "delay_seconds": self.delay_seconds
                                    }
                                )
                                
                                if scan_id:
                                    logger.info(f"Scan {scan_id} created and queued for repo {repo.repo_name} (worker will execute it)")
                                else:
                                    logger.error(f"Failed to create scan for repo {repo.repo_name}")
                    except Exception as e:
                        logger.error(f"Error processing repo {repo.id} for initial scan: {e}", exc_info=True)
                        continue
                        
        except Exception as e:
            logger.error(f"Error checking for initial scans: {e}", exc_info=True)
