"""Repo scan history repository (DDD port)."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from domain.entities.repo_scan_history_entry import RepoScanHistoryEntry


class RepoScanHistoryRepository(ABC):
    """Interface for repo scan history (read + add)."""

    @abstractmethod
    async def get_last_webhook_triggered_at(self, repo_ids: List[str]) -> Dict[str, datetime]:
        """Last scan created_at per repo where that scan was triggered by a webhook. Keys are repo_id (str)."""
        pass

    @abstractmethod
    async def add(
        self,
        repo_id: str,
        scan_id: Optional[str],
        branch: Optional[str],
        commit_hash: Optional[str],
        score: Optional[int],
        vulnerabilities: Dict[str, int],
    ) -> RepoScanHistoryEntry:
        """Append a history entry. Returns the created entry with id."""
        pass

    @abstractmethod
    async def get_latest_by_repo_ids(
        self, repo_ids: List[str]
    ) -> Dict[str, RepoScanHistoryEntry]:
        """Latest history entry per repo_id. Keys are repo_id (str)."""
        pass

    @abstractmethod
    async def get_history_page(
        self, repo_id: str, limit: int, offset: int
    ) -> Tuple[List[RepoScanHistoryEntry], int]:
        """History entries for repo, newest first. Returns (entries, total_count)."""
        pass
