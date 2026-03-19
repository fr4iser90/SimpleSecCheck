"""Database RepoScanHistory repository (DDD)."""
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, desc, func

from domain.entities.repo_scan_history_entry import RepoScanHistoryEntry
from domain.repositories.repo_scan_history_repository import RepoScanHistoryRepository
from infrastructure.database.models import RepoScanHistory as RepoScanHistoryModel
from infrastructure.database.adapter import db_adapter


def _model_to_entry(m: RepoScanHistoryModel) -> RepoScanHistoryEntry:
    return RepoScanHistoryEntry(
        id=str(m.id),
        repo_id=str(m.repo_id),
        scan_id=str(m.scan_id) if m.scan_id else None,
        branch=m.branch,
        commit_hash=m.commit_hash,
        score=m.score,
        vulnerabilities=dict(m.vulnerabilities) if m.vulnerabilities else {},
        created_at=m.created_at,
    )


class DatabaseRepoScanHistoryRepository(RepoScanHistoryRepository):
    """PostgreSQL implementation of RepoScanHistoryRepository."""

    def __init__(self, db_adapter_instance=None):
        self.db_adapter = db_adapter_instance or db_adapter

    async def add(
        self,
        repo_id: str,
        scan_id: Optional[str],
        branch: Optional[str],
        commit_hash: Optional[str],
        score: Optional[int],
        vulnerabilities: Dict[str, int],
    ) -> RepoScanHistoryEntry:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            model = RepoScanHistoryModel(
                repo_id=UUID(repo_id),
                scan_id=UUID(scan_id) if scan_id else None,
                branch=branch,
                commit_hash=commit_hash,
                score=score,
                vulnerabilities=vulnerabilities or {},
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return _model_to_entry(model)

    async def get_latest_by_repo_ids(
        self, repo_ids: List[str]
    ) -> Dict[str, RepoScanHistoryEntry]:
        if not repo_ids:
            return {}
        await self.db_adapter.ensure_initialized()
        uuids = [UUID(rid) for rid in repo_ids]
        async with self.db_adapter.async_session() as session:
            result = await session.execute(
                select(RepoScanHistoryModel)
                .where(RepoScanHistoryModel.repo_id.in_(uuids))
                .order_by(desc(RepoScanHistoryModel.created_at))
            )
            rows = result.scalars().all()
        out: Dict[str, RepoScanHistoryEntry] = {}
        for r in rows:
            rid = str(r.repo_id)
            if rid not in out:
                out[rid] = _model_to_entry(r)
        return out

    async def get_history_page(
        self, repo_id: str, limit: int, offset: int
    ) -> Tuple[List[RepoScanHistoryEntry], int]:
        await self.db_adapter.ensure_initialized()
        repo_uuid = UUID(repo_id)
        async with self.db_adapter.async_session() as session:
            count_result = await session.execute(
                select(func.count(RepoScanHistoryModel.id)).where(
                    RepoScanHistoryModel.repo_id == repo_uuid
                )
            )
            total = count_result.scalar() or 0
            history_result = await session.execute(
                select(RepoScanHistoryModel)
                .where(RepoScanHistoryModel.repo_id == repo_uuid)
                .order_by(desc(RepoScanHistoryModel.created_at))
                .limit(limit)
                .offset(offset)
            )
            rows = history_result.scalars().all()
        return [_model_to_entry(r) for r in rows], total
