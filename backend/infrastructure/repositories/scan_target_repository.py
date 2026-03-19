"""
Database ScanTarget Repository Implementation

Single source of truth for user_scan_targets table.
"""
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_

from domain.entities.scan_target import ScanTarget
from domain.value_objects.auto_scan_config import AutoScanConfig
from domain.repositories.scan_target_repository import ScanTargetRepository
from infrastructure.database.models import UserScanTarget
from infrastructure.database.adapter import db_adapter

logger = logging.getLogger(__name__)


def _model_to_entity(m: UserScanTarget) -> ScanTarget:
    """Convert DB model to domain entity."""
    return ScanTarget(
        id=str(m.id),
        user_id=str(m.user_id),
        type=m.type or "",
        source=m.source or "",
        display_name=m.display_name or "",
        auto_scan=AutoScanConfig.from_dict(m.auto_scan if isinstance(m.auto_scan, dict) else {}),
        config=dict(m.config or {}),
        created_at=m.created_at or datetime.utcnow(),
        updated_at=m.updated_at or datetime.utcnow(),
    )


def _entity_to_model(t: ScanTarget) -> dict:
    """Convert domain entity to dict for create/update."""
    return {
        "user_id": UUID(t.user_id) if t.user_id else None,
        "type": t.type,
        "source": t.source,
        "display_name": t.display_name or None,
        "auto_scan": t.auto_scan.to_dict(),
        "config": t.config,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }


class DatabaseScanTargetRepository(ScanTargetRepository):
    """PostgreSQL implementation of ScanTargetRepository."""

    def __init__(self, db_adapter_instance=None):
        self.db_adapter = db_adapter_instance or db_adapter

    async def create(self, target: ScanTarget) -> ScanTarget:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            model = UserScanTarget(
                id=UUID(target.id) if target.id else UUID(),
                **_entity_to_model(target),
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return _model_to_entity(model)

    async def get_by_id(self, target_id: str, user_id: str) -> Optional[ScanTarget]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            q = select(UserScanTarget).where(
                UserScanTarget.id == UUID(target_id),
                UserScanTarget.user_id == UUID(user_id),
            )
            r = await session.execute(q)
            m = r.scalar_one_or_none()
            return _model_to_entity(m) if m else None

    async def list_by_user(
        self,
        user_id: str,
        target_type: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> List[ScanTarget]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            q = select(UserScanTarget).where(UserScanTarget.user_id == UUID(user_id))
            if target_type:
                q = q.where(UserScanTarget.type == target_type)
            q = q.order_by(UserScanTarget.updated_at.desc()).limit(limit).offset(offset)
            r = await session.execute(q)
            return [_model_to_entity(m) for m in r.scalars().all()]

    async def list_with_auto_scan_interval(self, limit: int = 500) -> List[ScanTarget]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            q = (
                select(UserScanTarget)
                .order_by(UserScanTarget.updated_at.desc())
                .limit(limit * 2)
            )
            r = await session.execute(q)
            rows = r.scalars().all()
        out = []
        for m in rows:
            t = _model_to_entity(m)
            if t.auto_scan.enabled and t.auto_scan.mode == "interval" and (t.auto_scan.interval_seconds or 0) > 0:
                out.append(t)
                if len(out) >= limit:
                    break
        return out

    async def update(self, target: ScanTarget) -> ScanTarget:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            q = select(UserScanTarget).where(
                UserScanTarget.id == UUID(target.id),
                UserScanTarget.user_id == UUID(target.user_id),
            )
            r = await session.execute(q)
            m = r.scalar_one_or_none()
            if not m:
                raise ValueError("Target not found")
            m.source = target.source
            m.display_name = target.display_name or None
            m.auto_scan = target.auto_scan.to_dict()
            m.config = target.config
            m.updated_at = datetime.utcnow()
            await session.commit()
            await session.refresh(m)
            return _model_to_entity(m)

    async def delete(self, target_id: str, user_id: str) -> bool:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            q = select(UserScanTarget).where(
                UserScanTarget.id == UUID(target_id),
                UserScanTarget.user_id == UUID(user_id),
            )
            r = await session.execute(q)
            m = r.scalar_one_or_none()
            if not m:
                return False
            await session.delete(m)
            await session.commit()
            return True

    async def exists_for_user(self, user_id: str, source: str, target_type: str) -> bool:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            q = select(UserScanTarget.id).where(
                UserScanTarget.user_id == UUID(user_id),
                UserScanTarget.source == source,
                UserScanTarget.type == target_type,
            ).limit(1)
            r = await session.execute(q)
            return r.scalar_one_or_none() is not None
