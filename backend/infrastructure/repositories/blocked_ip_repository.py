"""
Database BlockedIP Repository Implementation.
"""
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from uuid import UUID
from sqlalchemy import select, func

from domain.repositories.blocked_ip_repository import BlockedIPRepository
from domain.datetime_serialization import isoformat_utc
from domain.entities.blocked_ip import BlockedIP
from infrastructure.database.models import BlockedIP as BlockedIPModel
from infrastructure.database.models import IPActivity
from infrastructure.database.adapter import db_adapter

logger = logging.getLogger(__name__)


def _model_to_entity(m: BlockedIPModel) -> BlockedIP:
    return BlockedIP(
        id=str(m.id),
        ip_address=str(m.ip_address) if m.ip_address else "",
        reason=m.reason,
        blocked_by=str(m.blocked_by) if m.blocked_by else None,
        blocked_at=m.blocked_at,
        expires_at=m.expires_at,
        is_active=m.is_active,
    )


class DatabaseBlockedIPRepository(BlockedIPRepository):
    """PostgreSQL implementation of BlockedIPRepository."""

    def __init__(self, db_adapter_instance=None):
        self.db_adapter = db_adapter_instance or db_adapter

    async def list_all(self, active_only: bool = True, limit: int = 500) -> List[BlockedIP]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            q = select(BlockedIPModel).order_by(BlockedIPModel.blocked_at.desc()).limit(limit)
            if active_only:
                q = q.where(BlockedIPModel.is_active == True)
            r = await session.execute(q)
            return [_model_to_entity(m) for m in r.scalars().all()]

    async def get_by_ip(self, ip_address: str) -> Optional[BlockedIP]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            r = await session.execute(
                select(BlockedIPModel).where(BlockedIPModel.ip_address == ip_address)
            )
            m = r.scalar_one_or_none()
            return _model_to_entity(m) if m else None

    async def create(self, ip_address: str, reason: Optional[str] = None, blocked_by: Optional[str] = None, expires_at: Optional[datetime] = None) -> BlockedIP:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            existing = await session.execute(
                select(BlockedIPModel).where(BlockedIPModel.ip_address == ip_address)
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"IP {ip_address} is already blocked")
            model = BlockedIPModel(
                ip_address=ip_address,
                reason=reason,
                blocked_by=UUID(blocked_by) if blocked_by else None,
                expires_at=expires_at,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return _model_to_entity(model)

    async def update(self, blocked_ip: BlockedIP) -> BlockedIP:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            r = await session.execute(
                select(BlockedIPModel).where(BlockedIPModel.id == UUID(blocked_ip.id))
            )
            m = r.scalar_one_or_none()
            if not m:
                raise ValueError("BlockedIP not found")
            m.reason = blocked_ip.reason
            m.blocked_by = UUID(blocked_ip.blocked_by) if blocked_ip.blocked_by else None
            m.blocked_at = blocked_ip.blocked_at
            m.expires_at = blocked_ip.expires_at
            m.is_active = blocked_ip.is_active
            await session.commit()
            await session.refresh(m)
            return _model_to_entity(m)

    async def delete_by_ip(self, ip_address: str) -> bool:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            r = await session.execute(
                select(BlockedIPModel).where(BlockedIPModel.ip_address == ip_address)
            )
            m = r.scalar_one_or_none()
            if not m:
                return False
            m.is_active = False
            await session.commit()
            return True

    async def get_activity_stats(self, since: Optional[datetime] = None, ip_address: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            q = select(IPActivity).order_by(IPActivity.count.desc()).limit(limit)
            if since is not None:
                q = q.where(IPActivity.created_at >= since)
            if ip_address is not None:
                q = q.where(IPActivity.ip_address == ip_address)
            r = await session.execute(q)
            rows = r.scalars().all()
            return [
                {
                    "ip_address": str(a.ip_address),
                    "event_type": a.event_type,
                    "count": a.count,
                    "window_start": isoformat_utc(a.window_start),
                    "metadata": a.activity_metadata or {},
                }
                for a in rows
            ]

    async def get_stats(self, activity_since: Optional[datetime] = None) -> Dict[str, int]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            blocked_count = await session.execute(
                select(func.count(BlockedIPModel.id)).where(BlockedIPModel.is_active == True)
            )
            total_blocked = blocked_count.scalar() or 0
            activity_count_q = select(func.count(IPActivity.id))
            if activity_since is not None:
                activity_count_q = activity_count_q.where(IPActivity.created_at >= activity_since)
            activity_count = await session.execute(activity_count_q)
            total_activity = activity_count.scalar() or 0
            return {"total_blocked": total_blocked, "total_activity_24h": total_activity}
