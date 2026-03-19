"""
Database User Repository Implementation (DDD).
"""
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select

from domain.entities.user import User, UserRole
from domain.repositories.user_repository import UserRepository
from infrastructure.database.models import User as UserModel
from infrastructure.database.adapter import db_adapter

logger = logging.getLogger(__name__)


def _model_to_entity(m: UserModel) -> User:
    """Map DB model to domain entity."""
    return User(
        id=str(m.id),
        username=m.username or "",
        email=m.email or "",
        password_hash=m.password_hash or "",
        role=UserRole(getattr(m.role, "value", m.role) or "user"),
        is_active=bool(m.is_active),
        is_verified=bool(m.is_verified),
        created_at=m.created_at or datetime.utcnow(),
        updated_at=m.updated_at or datetime.utcnow(),
        last_login=m.last_login,
        metadata=dict(m.user_metadata) if m.user_metadata else {},
    )


def _entity_to_model(u: User) -> dict:
    """Map domain entity to dict for create/update."""
    return {
        "username": u.username,
        "email": u.email,
        "password_hash": u.password_hash,
        "role": u.role.value,
        "is_active": u.is_active,
        "is_verified": u.is_verified,
        "created_at": u.created_at,
        "updated_at": u.updated_at,
        "last_login": u.last_login,
        "user_metadata": u.metadata,
    }


class DatabaseUserRepository(UserRepository):
    """PostgreSQL implementation of UserRepository."""

    def __init__(self, db_adapter_instance=None):
        self.db_adapter = db_adapter_instance or db_adapter

    async def get_by_id(self, user_id: str) -> Optional[User]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            r = await session.execute(
                select(UserModel).where(UserModel.id == UUID(user_id))
            )
            m = r.scalar_one_or_none()
            return _model_to_entity(m) if m else None

    async def get_by_email(self, email: str, active_only: bool = True) -> Optional[User]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            q = select(UserModel).where(UserModel.email == email)
            if active_only:
                q = q.where(UserModel.is_active == True)
            r = await session.execute(q)
            m = r.scalar_one_or_none()
            return _model_to_entity(m) if m else None

    async def get_by_username(self, username: str) -> Optional[User]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            r = await session.execute(
                select(UserModel).where(UserModel.username == username)
            )
            m = r.scalar_one_or_none()
            return _model_to_entity(m) if m else None

    async def list_all(self, limit: int = 500, offset: int = 0) -> List[User]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            r = await session.execute(
                select(UserModel).order_by(UserModel.created_at.desc()).limit(limit).offset(offset)
            )
            return [_model_to_entity(m) for m in r.scalars().all()]

    async def create(self, user: User) -> User:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            kwargs = _entity_to_model(user)
            if user.id and str(user.id).strip():
                model = UserModel(id=UUID(user.id), **kwargs)
            else:
                model = UserModel(**kwargs)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return _model_to_entity(model)

    async def update(self, user: User) -> User:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            r = await session.execute(
                select(UserModel).where(UserModel.id == UUID(user.id))
            )
            m = r.scalar_one_or_none()
            if not m:
                raise ValueError("User not found")
            for k, v in _entity_to_model(user).items():
                setattr(m, k, v)
            await session.commit()
            await session.refresh(m)
            return _model_to_entity(m)

    async def delete_by_id(self, user_id: str) -> bool:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            r = await session.execute(select(UserModel).where(UserModel.id == UUID(user_id)))
            m = r.scalar_one_or_none()
            if not m:
                return False
            await session.delete(m)
            await session.commit()
            return True

    async def has_admin_user(self) -> bool:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            r = await session.execute(
                select(UserModel).where(
                    UserModel.role == "admin",
                    UserModel.is_active == True,
                ).limit(1)
            )
            return r.scalar_one_or_none() is not None
