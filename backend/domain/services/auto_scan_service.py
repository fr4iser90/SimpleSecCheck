"""
Auto-Scan Service

Service for managing automatic scanning of GitHub repositories using a round-robin approach.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from infrastructure.database.adapter import db_adapter
from infrastructure.database.models import UserGitHubRepo, RepoScanHistory
from sqlalchemy import select, and_, or_, func
from uuid import UUID

logger = logging.getLogger(__name__)


class AutoScanService:
    """Service for managing automatic repository scanning."""
    
    @staticmethod
    async def get_next_repo_to_scan() -> Optional[Dict[str, Any]]:
        """
        Get the next repository to scan using round-robin approach.
        
        Returns the repository that:
        1. Has auto_scan_enabled = True
        2. Hasn't been scanned recently (based on scan_frequency)
        3. Is the oldest since last scan (fair distribution)
        
        Returns:
            Repository dict or None if no repos need scanning
        """
        try:
            async with db_adapter.async_session() as session:
                # Get all repos with auto-scan enabled
                repos_result = await session.execute(
                    select(UserGitHubRepo).where(
                        UserGitHubRepo.auto_scan_enabled == True
                    )
                )
                repos = repos_result.scalars().all()
                
                if not repos:
                    return None
                
                # Get last scan for each repo
                repos_with_last_scan = []
                for repo in repos:
                    # Get last scan
                    history_result = await session.execute(
                        select(RepoScanHistory)
                        .where(RepoScanHistory.repo_id == repo.id)
                        .order_by(RepoScanHistory.created_at.desc())
                        .limit(1)
                    )
                    last_history = history_result.scalar_one_or_none()
                    
                    # Check if repo needs scanning based on frequency
                    needs_scan = False
                    last_scan_time = None
                    
                    if last_history:
                        last_scan_time = last_history.created_at
                        time_since_scan = datetime.utcnow() - last_scan_time
                        
                        if repo.scan_frequency == "daily":
                            needs_scan = time_since_scan >= timedelta(days=1)
                        elif repo.scan_frequency == "weekly":
                            needs_scan = time_since_scan >= timedelta(weeks=1)
                        elif repo.scan_frequency == "on_push":
                            # For on_push, we rely on webhooks, but can also scan if never scanned
                            needs_scan = False  # Webhook handles this
                        else:  # manual
                            needs_scan = False
                    else:
                        # Never scanned, needs initial scan
                        needs_scan = True
                    
                    if needs_scan or last_scan_time is None:
                        repos_with_last_scan.append({
                            "repo": repo,
                            "last_scan": last_scan_time,
                            "priority": last_scan_time.timestamp() if last_scan_time else 0
                        })
                
                if not repos_with_last_scan:
                    return None
                
                # Sort by last scan time (oldest first) for round-robin
                repos_with_last_scan.sort(key=lambda x: x["priority"])
                
                # Get the oldest repo
                next_repo_data = repos_with_last_scan[0]
                repo = next_repo_data["repo"]
                
                return {
                    "id": str(repo.id),
                    "repo_url": repo.repo_url,
                    "repo_name": repo.repo_name,
                    "branch": repo.branch,
                    "user_id": str(repo.user_id),
                    "github_token": repo.github_token
                }
        except Exception as e:
            logger.error(f"Failed to get next repo to scan: {e}", exc_info=True)
            return None
    
    @staticmethod
    async def get_user_repos_scan_queue(user_id: str) -> List[Dict[str, Any]]:
        """
        Get all repos for a user that are in the scan queue (round-robin order).
        
        Args:
            user_id: User ID
            
        Returns:
            List of repos in queue order
        """
        try:
            async with db_adapter.async_session() as session:
                user_uuid = UUID(user_id)
                
                # Get all repos for user
                repos_result = await session.execute(
                    select(UserGitHubRepo)
                    .where(UserGitHubRepo.user_id == user_uuid)
                    .order_by(UserGitHubRepo.created_at.desc())
                )
                repos = repos_result.scalars().all()
                
                repos_with_info = []
                for repo in repos:
                    # Get last scan
                    history_result = await session.execute(
                        select(RepoScanHistory)
                        .where(RepoScanHistory.repo_id == repo.id)
                        .order_by(RepoScanHistory.created_at.desc())
                        .limit(1)
                    )
                    last_history = history_result.scalar_one_or_none()
                    
                    repos_with_info.append({
                        "id": str(repo.id),
                        "repo_url": repo.repo_url,
                        "repo_name": repo.repo_name,
                        "branch": repo.branch,
                        "auto_scan_enabled": repo.auto_scan_enabled,
                        "last_scan": last_history.created_at if last_history else None,
                        "score": last_history.score if last_history else None
                    })
                
                # Sort by last scan (oldest first) for round-robin
                repos_with_info.sort(
                    key=lambda x: x["last_scan"].timestamp() if x["last_scan"] else 0
                )
                
                return repos_with_info
        except Exception as e:
            logger.error(f"Failed to get user repos queue: {e}", exc_info=True)
            return []
    
    @staticmethod
    async def record_scan_result(
        repo_id: str,
        scan_id: Optional[str],
        branch: str,
        commit_hash: Optional[str],
        score: Optional[int],
        vulnerabilities: Optional[Dict[str, int]]
    ) -> None:
        """
        Record a scan result for a repository.
        
        Args:
            repo_id: Repository ID
            scan_id: Scan ID (optional)
            branch: Branch that was scanned
            commit_hash: Commit hash (optional)
            score: Security score (0-100)
            vulnerabilities: Vulnerability counts
        """
        try:
            async with db_adapter.async_session() as session:
                repo_uuid = UUID(repo_id)
                scan_uuid = UUID(scan_id) if scan_id else None
                
                history_entry = RepoScanHistory(
                    repo_id=repo_uuid,
                    scan_id=scan_uuid,
                    branch=branch,
                    commit_hash=commit_hash,
                    score=score,
                    vulnerabilities=vulnerabilities or {}
                )
                
                session.add(history_entry)
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to record scan result: {e}", exc_info=True)
