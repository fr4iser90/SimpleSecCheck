"""GitHub Repo Repository Interface (DDD port)."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from domain.entities.github_repo import GitHubRepo


class GitHubRepoRepository(ABC):
    """Interface for user GitHub repo persistence."""

    @abstractmethod
    async def list_auto_scan_enabled(
        self, created_before: Optional[datetime] = None
    ) -> List[GitHubRepo]:
        """List repos with auto_scan_enabled=True, optionally created before given time."""
        pass

    @abstractmethod
    async def list_by_user(self, user_id: str) -> List[GitHubRepo]:
        """List repos for user, newest first."""
        pass

    @abstractmethod
    async def get_by_id(self, repo_id: str, user_id: str) -> Optional[GitHubRepo]:
        """Get repo by id; must belong to user."""
        pass

    @abstractmethod
    async def get_by_user_and_url(
        self,
        user_id: str,
        repo_url: str,
    ) -> Optional[GitHubRepo]:
        """Get repo by user and exact repo_url."""
        pass

    @abstractmethod
    async def get_by_repo_url_with_auto_scan(self, repo_url: str) -> Optional[GitHubRepo]:
        """Get repo by exact repo_url where auto_scan_enabled and scan_on_push are True (e.g. for webhooks)."""
        pass

    @abstractmethod
    async def create(self, repo: GitHubRepo) -> GitHubRepo:
        """Create a new repo. Returns created repo with id."""
        pass

    @abstractmethod
    async def update(self, repo: GitHubRepo) -> GitHubRepo:
        """Update existing repo."""
        pass

    @abstractmethod
    async def delete(self, repo_id: str, user_id: str) -> bool:
        """Delete repo. Returns True if deleted."""
        pass
