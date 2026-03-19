"""
GitHub Repo Application Service (DDD).
Uses GitHubRepoRepository only.
"""
from typing import List, Optional

from domain.entities.github_repo import GitHubRepo
from domain.repositories.github_repo_repository import GitHubRepoRepository


class GitHubRepoService:
    """Application service for user GitHub repo operations."""

    def __init__(self, github_repo_repository: GitHubRepoRepository):
        self._repo = github_repo_repository

    async def list_by_user(self, user_id: str) -> List[GitHubRepo]:
        return await self._repo.list_by_user(user_id)

    async def get_by_id(self, repo_id: str, user_id: str) -> Optional[GitHubRepo]:
        return await self._repo.get_by_id(repo_id, user_id)

    async def get_by_user_and_url(
        self,
        user_id: str,
        repo_url: str,
    ) -> Optional[GitHubRepo]:
        return await self._repo.get_by_user_and_url(user_id, repo_url)

    async def get_by_repo_url_with_auto_scan(self, repo_url: str) -> Optional[GitHubRepo]:
        """Find repo by URL with auto_scan and scan_on_push enabled (e.g. for webhooks)."""
        return await self._repo.get_by_repo_url_with_auto_scan(repo_url)

    async def create(
        self,
        user_id: str,
        repo_url: str,
        repo_name: str,
        *,
        repo_owner: Optional[str] = None,
        branch: str = "main",
        auto_scan_enabled: bool = True,
        scan_on_push: bool = True,
        scan_frequency: str = "on_push",
        scanners: Optional[List[str]] = None,
        github_token: Optional[str] = None,
    ) -> GitHubRepo:
        """Create a new repo. Caller should validate URL and check duplicate."""
        from datetime import datetime
        now = datetime.utcnow()
        repo = GitHubRepo(
            id="",
            user_id=user_id,
            repo_url=repo_url,
            repo_owner=repo_owner,
            repo_name=repo_name,
            branch=branch,
            auto_scan_enabled=auto_scan_enabled,
            scan_on_push=scan_on_push,
            scan_frequency=scan_frequency,
            scanners=scanners,
            created_at=now,
            updated_at=now,
            github_token=github_token,
        )
        return await self._repo.create(repo)

    async def update(
        self,
        repo_id: str,
        user_id: str,
        *,
        branch: Optional[str] = None,
        auto_scan_enabled: Optional[bool] = None,
        scan_on_push: Optional[bool] = None,
        scan_frequency: Optional[str] = None,
        scanners: Optional[List[str]] = None,
    ) -> GitHubRepo:
        """Update repo. Only provided fields are updated."""
        repo = await self._repo.get_by_id(repo_id, user_id)
        if not repo:
            raise ValueError("Repository not found")
        if branch is not None:
            repo.branch = branch
        if auto_scan_enabled is not None:
            repo.auto_scan_enabled = auto_scan_enabled
        if scan_on_push is not None:
            repo.scan_on_push = scan_on_push
        if scan_frequency is not None:
            repo.scan_frequency = scan_frequency
        if scanners is not None:
            repo.scanners = scanners
        from datetime import datetime
        repo.updated_at = datetime.utcnow()
        return await self._repo.update(repo)

    async def delete(self, repo_id: str, user_id: str) -> bool:
        return await self._repo.delete(repo_id, user_id)
