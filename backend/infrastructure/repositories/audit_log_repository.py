"""Database AuditLog repository implementation."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select, desc, and_, or_, func

from domain.repositories.audit_log_repository import AuditLogRepository
from domain.datetime_serialization import isoformat_utc
from infrastructure.database.models import AuditLog as AuditLogModel
from infrastructure.database.adapter import db_adapter


class DatabaseAuditLogRepository(AuditLogRepository):
    """PostgreSQL implementation of AuditLogRepository."""

    def __init__(self, db_adapter_instance=None):
        self.db_adapter = db_adapter_instance or db_adapter

    async def add(
        self,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        action_type: str = "",
        target: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        result: str = "success",
    ) -> None:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            entry = AuditLogModel(
                user_id=UUID(user_id) if user_id else None,
                user_email=user_email,
                action_type=action_type,
                target=target,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent,
                result=result,
            )
            session.add(entry)
            await session.commit()

    async def get_entries(
        self,
        limit: int = 100,
        offset: int = 0,
        user_id: Optional[str] = None,
        action_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search: Optional[str] = None,
    ) -> tuple:  # (List[Dict], int)
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            conditions = []
            if user_id:
                conditions.append(AuditLogModel.user_id == UUID(user_id))
            if action_type:
                conditions.append(AuditLogModel.action_type == action_type)
            if start_date:
                conditions.append(AuditLogModel.created_at >= start_date)
            if end_date:
                conditions.append(AuditLogModel.created_at <= end_date)
            if search:
                conditions.append(
                    or_(
                        AuditLogModel.target.ilike(f"%{search}%"),
                        AuditLogModel.user_email.ilike(f"%{search}%"),
                    )
                )
            base = select(AuditLogModel)
            count_q = select(func.count()).select_from(AuditLogModel)
            if conditions:
                base = base.where(and_(*conditions))
                count_q = count_q.where(and_(*conditions))
            total_r = await session.execute(count_q)
            total = total_r.scalar() or 0
            q = base.order_by(desc(AuditLogModel.created_at)).limit(limit).offset(offset)
            r = await session.execute(q)
            rows = r.scalars().all()
            entries = [
                {
                    "id": str(e.id),
                    "user_id": str(e.user_id) if e.user_id else None,
                    "user_email": e.user_email,
                    "action_type": e.action_type,
                    "target": e.target,
                    "details": e.details or {},
                    "ip_address": str(e.ip_address) if e.ip_address else None,
                    "user_agent": e.user_agent,
                    "result": e.result,
                    "created_at": isoformat_utc(e.created_at),
                }
                for e in rows
            ]
            return (entries, total)
