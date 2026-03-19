"""Database API Key Repository Implementation (DDD)."""
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select

from domain.entities.api_key import ApiKey
from domain.repositories.api_key_repository import ApiKeyRepository
from infrastructure.database.models import APIKey as APIKeyModel
from infrastructure.database.adapter import db_adapter

logger = logging.getLogger(__name__)


def _model_to_entity(m: APIKeyModel) -> ApiKey:
    return ApiKey(
        id=str(m.id),
        user_id=str(m.user_id),
        name=m.name or "",
        key_hash=m.key_hash or "",
        created_at=m.created_at or datetime.utcnow(),
        last_used_at=m.last_used_at,
        expires_at=m.expires_at,
        is_active=bool(m.is_active),
    )


class DatabaseApiKeyRepository(ApiKeyRepository):
    """PostgreSQL implementation of ApiKeyRepository."""

    def __init__(self, db_adapter_instance=None):
        self.db_adapter = db_adapter_instance or db_adapter

    async def list_by_user(
        self,
        user_id: str,
        active_only: bool = True,
    ) -> List[ApiKey]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            q = (
                select(APIKeyModel)
                .where(APIKeyModel.user_id == UUID(user_id))
                .order_by(APIKeyModel.created_at.desc())
            )
            if active_only:
                q = q.where(APIKeyModel.is_active == True)
            r = await session.execute(q)
            return [_model_to_entity(m) for m in r.scalars().all()]

    async def create(
        self,
        user_id: str,
        name: str,
        key_hash: str,
        expires_at: Optional[datetime] = None,
    ) -> ApiKey:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            model = APIKeyModel(
                user_id=UUID(user_id),
                key_hash=key_hash,
                name=name,
                expires_at=expires_at,
                is_active=True,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return _model_to_entity(model)

    async def get_by_id(self, key_id: str, user_id: str) -> Optional[ApiKey]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            r = await session.execute(
                select(APIKeyModel).where(
                    APIKeyModel.id == UUID(key_id),
                    APIKeyModel.user_id == UUID(user_id),
                )
            )
            m = r.scalar_one_or_none()
            return _model_to_entity(m) if m else None

    async def revoke(self, key_id: str, user_id: str) -> bool:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            r = await session.execute(
                select(APIKeyModel).where(
                    APIKeyModel.id == UUID(key_id),
                    APIKeyModel.user_id == UUID(user_id),
                )
            )
            m = r.scalar_one_or_none()
            if not m:
                return False
            m.is_active = False
            await session.commit()
            return True
