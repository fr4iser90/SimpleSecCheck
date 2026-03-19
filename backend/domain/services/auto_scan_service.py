"""
Auto-Scan Service

Service for managing automatic scanning of GitHub repositories using a round-robin approach.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from infrastructure.container import (
    get_github_repo_repository,
    get_repo_scan_history_repository,
)

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
            repo_repo = get_github_repo_repository()
            history_repo = get_repo_scan_history_repository()

            repos = await repo_repo.list_auto_scan_enabled()
            if not repos:
                return None

            repo_ids = [r.id for r in repos]
            latest_by_repo = await history_repo.get_latest_by_repo_ids(repo_ids)

            repos_with_last_scan = []
            for repo in repos:
                last_entry = latest_by_repo.get(repo.id)
                last_scan_time = last_entry.created_at if last_entry else None

                needs_scan = False
                if last_entry:
                    time_since_scan = datetime.utcnow() - last_entry.created_at
                    if repo.scan_frequency == "daily":
                        needs_scan = time_since_scan >= timedelta(days=1)
                    elif repo.scan_frequency == "weekly":
                        needs_scan = time_since_scan >= timedelta(weeks=1)
                    elif repo.scan_frequency == "on_push":
                        needs_scan = False
                    else:
                        needs_scan = False
                else:
                    needs_scan = True

                if needs_scan or last_scan_time is None:
                    repos_with_last_scan.append({
                        "repo": repo,
                        "last_scan": last_scan_time,
                        "priority": last_scan_time.timestamp() if last_scan_time else 0,
                    })

            if not repos_with_last_scan:
                return None

            repos_with_last_scan.sort(key=lambda x: x["priority"])
            next_repo_data = repos_with_last_scan[0]
            repo = next_repo_data["repo"]

            return {
                "id": repo.id,
                "repo_url": repo.repo_url,
                "repo_name": repo.repo_name,
                "branch": repo.branch,
                "user_id": repo.user_id,
                "github_token": repo.github_token,
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
            repo_repo = get_github_repo_repository()
            history_repo = get_repo_scan_history_repository()

            repos = await repo_repo.list_by_user(user_id)
            if not repos:
                return []

            repo_ids = [r.id for r in repos]
            latest_by_repo = await history_repo.get_latest_by_repo_ids(repo_ids)

            repos_with_info = []
            for repo in repos:
                last_entry = latest_by_repo.get(repo.id)
                repos_with_info.append({
                    "id": repo.id,
                    "repo_url": repo.repo_url,
                    "repo_name": repo.repo_name,
                    "branch": repo.branch,
                    "auto_scan_enabled": repo.auto_scan_enabled,
                    "last_scan": last_entry.created_at if last_entry else None,
                    "score": last_entry.score if last_entry else None,
                })

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
        branch: Optional[str],
        commit_hash: Optional[str],
        score: Optional[int],
        vulnerabilities: Optional[Dict[str, int]],
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
            history_repo = get_repo_scan_history_repository()
            await history_repo.add(
                repo_id=repo_id,
                scan_id=scan_id,
                branch=branch,
                commit_hash=commit_hash,
                score=score,
                vulnerabilities=vulnerabilities or {},
            )
        except Exception as e:
            logger.error(f"Failed to record scan result: {e}", exc_info=True)
