"""Database GitHub Repo Repository Implementation (DDD)."""
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select

from domain.entities.github_repo import GitHubRepo
from domain.repositories.github_repo_repository import GitHubRepoRepository
from infrastructure.database.models import UserGitHubRepo as UserGitHubRepoModel
from infrastructure.database.adapter import db_adapter

logger = logging.getLogger(__name__)


def _model_to_entity(m: UserGitHubRepoModel) -> GitHubRepo:
    return GitHubRepo(
        id=str(m.id),
        user_id=str(m.user_id),
        repo_url=m.repo_url or "",
        repo_owner=m.repo_owner,
        repo_name=m.repo_name or "",
        branch=m.branch or "main",
        auto_scan_enabled=bool(m.auto_scan_enabled),
        scan_on_push=bool(m.scan_on_push),
        scan_frequency=m.scan_frequency or "on_push",
        scanners=list(m.scanners) if m.scanners else None,
        created_at=m.created_at or datetime.utcnow(),
        updated_at=m.updated_at or datetime.utcnow(),
        github_token=m.github_token,
        webhook_secret=m.webhook_secret,
    )


def _entity_to_model(e: GitHubRepo) -> dict:
    return {
        "user_id": UUID(e.user_id),
        "repo_url": e.repo_url,
        "repo_owner": e.repo_owner,
        "repo_name": e.repo_name,
        "branch": e.branch,
        "auto_scan_enabled": e.auto_scan_enabled,
        "scan_on_push": e.scan_on_push,
        "scan_frequency": e.scan_frequency,
        "scanners": e.scanners,
        "github_token": e.github_token,
        "webhook_secret": e.webhook_secret,
    }


class DatabaseGitHubRepoRepository(GitHubRepoRepository):
    """PostgreSQL implementation of GitHubRepoRepository."""

    def __init__(self, db_adapter_instance=None):
        self.db_adapter = db_adapter_instance or db_adapter

    async def list_auto_scan_enabled(
        self, created_before: Optional[datetime] = None
    ) -> List[GitHubRepo]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            q = select(UserGitHubRepoModel).where(
                UserGitHubRepoModel.auto_scan_enabled == True
            )
            if created_before is not None:
                q = q.where(UserGitHubRepoModel.created_at <= created_before)
            q = q.order_by(UserGitHubRepoModel.created_at.desc())
            r = await session.execute(q)
            return [_model_to_entity(m) for m in r.scalars().all()]

    async def list_by_user(self, user_id: str) -> List[GitHubRepo]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            r = await session.execute(
                select(UserGitHubRepoModel)
                .where(UserGitHubRepoModel.user_id == UUID(user_id))
                .order_by(UserGitHubRepoModel.created_at.desc())
            )
            return [_model_to_entity(m) for m in r.scalars().all()]

    async def get_by_id(self, repo_id: str, user_id: str) -> Optional[GitHubRepo]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            r = await session.execute(
                select(UserGitHubRepoModel).where(
                    UserGitHubRepoModel.id == UUID(repo_id),
                    UserGitHubRepoModel.user_id == UUID(user_id),
                )
            )
            m = r.scalar_one_or_none()
            return _model_to_entity(m) if m else None

    async def get_by_user_and_url(
        self,
        user_id: str,
        repo_url: str,
    ) -> Optional[GitHubRepo]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            r = await session.execute(
                select(UserGitHubRepoModel).where(
                    UserGitHubRepoModel.user_id == UUID(user_id),
                    UserGitHubRepoModel.repo_url == repo_url,
                )
            )
            m = r.scalar_one_or_none()
            return _model_to_entity(m) if m else None

    async def get_by_repo_url_with_auto_scan(self, repo_url: str) -> Optional[GitHubRepo]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            r = await session.execute(
                select(UserGitHubRepoModel).where(
                    UserGitHubRepoModel.repo_url == repo_url,
                    UserGitHubRepoModel.auto_scan_enabled == True,
                    UserGitHubRepoModel.scan_on_push == True,
                )
            )
            m = r.scalar_one_or_none()
            return _model_to_entity(m) if m else None

    async def create(self, repo: GitHubRepo) -> GitHubRepo:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            kwargs = _entity_to_model(repo)
            model = UserGitHubRepoModel(**kwargs)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return _model_to_entity(model)

    async def update(self, repo: GitHubRepo) -> GitHubRepo:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            r = await session.execute(
                select(UserGitHubRepoModel).where(
                    UserGitHubRepoModel.id == UUID(repo.id),
                    UserGitHubRepoModel.user_id == UUID(repo.user_id),
                )
            )
            m = r.scalar_one_or_none()
            if not m:
                raise ValueError("Repository not found")
            for k, v in _entity_to_model(repo).items():
                setattr(m, k, v)
            m.updated_at = datetime.utcnow()
            await session.commit()
            await session.refresh(m)
            return _model_to_entity(m)

    async def delete(self, repo_id: str, user_id: str) -> bool:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            r = await session.execute(
                select(UserGitHubRepoModel).where(
                    UserGitHubRepoModel.id == UUID(repo_id),
                    UserGitHubRepoModel.user_id == UUID(user_id),
                )
            )
            m = r.scalar_one_or_none()
            if not m:
                return False
            await session.delete(m)
            await session.commit()
            return True
