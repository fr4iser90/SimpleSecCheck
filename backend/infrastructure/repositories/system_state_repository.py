"""Database SystemState repository (DDD)."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select

from domain.entities.system_state import SystemState, SetupStatus
from domain.repositories.system_state_repository import SystemStateRepository
from infrastructure.database.models import (
    SystemState as SystemStateModel,
    SYSTEM_STATE_SINGLETON_ID,
)
from infrastructure.database.adapter import db_adapter


def _model_to_entity(m: SystemStateModel) -> SystemState:
    state = SystemState()
    state.id = str(m.id)
    state.setup_status = SetupStatus(getattr(m.setup_status, "value", m.setup_status) or "not_initialized")
    state.version = m.version or "1.0.0"
    state.auth_mode = m.auth_mode or "free"
    state.config = dict(m.config) if m.config else {}
    state.setup_token_hash = m.setup_token_hash
    state.setup_token_created_at = m.setup_token_created_at
    state.created_at = m.created_at or datetime.utcnow()
    state.updated_at = m.updated_at or datetime.utcnow()
    state.setup_completed_at = m.setup_completed_at
    state.database_initialized = bool(m.database_initialized)
    state.admin_user_created = bool(m.admin_user_created)
    state.system_configured = bool(m.system_configured)
    state.setup_attempts = int(m.setup_attempts or 0)
    state.last_setup_attempt = m.last_setup_attempt
    state.setup_locked = bool(m.setup_locked)
    return state


def _entity_to_model(state: SystemState) -> SystemStateModel:
    return SystemStateModel(
        id=UUID(state.id) if state.id else SYSTEM_STATE_SINGLETON_ID,
        setup_status=state.setup_status.value,
        version=state.version,
        auth_mode=state.auth_mode,
        config=state.config,
        setup_token_hash=state.setup_token_hash,
        setup_token_created_at=state.setup_token_created_at,
        created_at=state.created_at,
        updated_at=state.updated_at,
        setup_completed_at=state.setup_completed_at,
        database_initialized=state.database_initialized,
        admin_user_created=state.admin_user_created,
        system_configured=state.system_configured,
        setup_attempts=state.setup_attempts,
        last_setup_attempt=state.last_setup_attempt,
        setup_locked=state.setup_locked,
    )


class DatabaseSystemStateRepository(SystemStateRepository):
    """PostgreSQL implementation of SystemStateRepository."""

    def __init__(self, db_adapter_instance=None):
        self.db_adapter = db_adapter_instance or db_adapter

    async def table_exists(self) -> bool:
        return await self.db_adapter.check_table_exists("system_state")

    async def get_singleton(self) -> Optional[SystemState]:
        if not await self.table_exists():
            return None
        async with self.db_adapter.async_session() as session:
            result = await session.execute(select(SystemStateModel).limit(1))
            m = result.scalar_one_or_none()
            return _model_to_entity(m) if m else None

    async def save(self, state: SystemState) -> SystemState:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            result = await session.execute(select(SystemStateModel).limit(1))
            m = result.scalar_one_or_none()
            if not m:
                m = _entity_to_model(state)
                session.add(m)
            else:
                m.setup_status = state.setup_status.value
                m.version = state.version
                m.auth_mode = state.auth_mode
                m.config = state.config
                m.setup_token_hash = state.setup_token_hash
                m.setup_token_created_at = state.setup_token_created_at
                m.updated_at = state.updated_at
                m.setup_completed_at = state.setup_completed_at
                m.database_initialized = state.database_initialized
                m.admin_user_created = state.admin_user_created
                m.system_configured = state.system_configured
                m.setup_attempts = state.setup_attempts
                m.last_setup_attempt = state.last_setup_attempt
                m.setup_locked = state.setup_locked
            await session.commit()
            await session.refresh(m)
            return _model_to_entity(m)
