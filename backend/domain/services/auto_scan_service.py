"""
Auto-Scan Service

Service for managing automatic scanning of GitHub repositories (round-robin periodic).
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from application.helpers.periodic_repo_scan import (
    commit_hash_from_scan_metadata,
    evaluate_periodic_repo_scan,
    history_entry_from_scan,
)
from infrastructure.container import (
    get_github_repo_repository,
    get_repo_scan_history_repository,
    get_scan_repository,
)

logger = logging.getLogger(__name__)


class AutoScanService:
    """Service for managing automatic repository scanning."""

    @staticmethod
    async def get_next_repo_to_scan(
        *,
        cooldown_seconds: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get the next repository due for a periodic scan (daily/weekly).

        Returns the oldest-last-scan repo that passes frequency, cooldown, and commit-diff checks.
        """
        try:
            repo_repo = get_github_repo_repository()
            history_repo = get_repo_scan_history_repository()
            scan_repo = get_scan_repository()

            repos = await repo_repo.list_auto_scan_enabled()
            if not repos:
                return None

            repo_ids = [r.id for r in repos]
            latest_by_repo = await history_repo.get_latest_by_repo_ids(repo_ids)

            cooldown = cooldown_seconds
            candidates: List[Dict[str, Any]] = []

            for repo in repos:
                last_entry = latest_by_repo.get(repo.id)
                if not last_entry:
                    last_scan = await scan_repo.find_latest_finished_scan_by_user_and_target(
                        repo.user_id, repo.repo_url
                    )
                    if last_scan:
                        finished_at = last_scan.completed_at or last_scan.created_at
                        if finished_at:
                            last_entry = history_entry_from_scan(
                                repo.id,
                                scan_id=str(last_scan.id),
                                branch=repo.branch,
                                commit_hash=commit_hash_from_scan_metadata(
                                    last_scan.metadata or {}
                                ),
                                created_at=finished_at,
                            )
                kwargs = {}
                if cooldown is not None:
                    kwargs["cooldown_seconds"] = cooldown
                should_scan, reason, head_sha = evaluate_periodic_repo_scan(
                    repo, last_entry, **kwargs
                )
                if not should_scan:
                    logger.debug(
                        "Periodic skip repo %s (%s): %s",
                        repo.repo_name,
                        repo.id,
                        reason,
                    )
                    continue

                last_scan_time = last_entry.created_at if last_entry else None
                candidates.append({
                    "repo": repo,
                    "last_scan": last_scan_time,
                    "priority": last_scan_time.timestamp() if last_scan_time else 0,
                    "head_sha": head_sha,
                    "reason": reason,
                })

            if not candidates:
                return None

            candidates.sort(key=lambda x: x["priority"])
            next_repo_data = candidates[0]
            repo = next_repo_data["repo"]

            return {
                "id": repo.id,
                "repo_url": repo.repo_url,
                "repo_name": repo.repo_name,
                "branch": repo.branch,
                "user_id": repo.user_id,
                "scanners": repo.scanners,
                "github_token": repo.github_token,
                "commit_hash": next_repo_data.get("head_sha"),
                "scan_reason": next_repo_data.get("reason"),
            }
        except Exception as e:
            logger.error("Failed to get next repo to scan: %s", e, exc_info=True)
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
                    "scan_frequency": repo.scan_frequency,
                    "last_scan": last_entry.created_at if last_entry else None,
                    "score": last_entry.score if last_entry else None,
                })

            repos_with_info.sort(
                key=lambda x: x["last_scan"].timestamp() if x["last_scan"] else 0
            )
            return repos_with_info
        except Exception as e:
            logger.error("Failed to get user repos queue: %s", e, exc_info=True)
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
            logger.error("Failed to record scan result: %s", e, exc_info=True)
