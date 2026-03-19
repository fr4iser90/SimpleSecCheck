"""Database ScannerToolSettings repository implementation."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select

from domain.repositories.scanner_tool_settings_repository import ScannerToolSettingsRepository
from domain.entities.scanner_tool_settings import ScannerToolSettings
from infrastructure.database.models import ScannerToolSettings as ScannerToolSettingsModel
from infrastructure.database.adapter import db_adapter


def _model_to_entity(m: ScannerToolSettingsModel) -> ScannerToolSettings:
    return ScannerToolSettings(
        scanner_key=m.scanner_key,
        enabled=m.enabled,
        timeout_seconds=m.timeout_seconds,
        config=dict(m.config) if m.config else {},
        updated_at=m.updated_at,
        updated_by_user_id=str(m.updated_by_user_id) if m.updated_by_user_id else None,
    )


class DatabaseScannerToolSettingsRepository(ScannerToolSettingsRepository):
    """PostgreSQL implementation of ScannerToolSettingsRepository."""

    def __init__(self, db_adapter_instance=None):
        self.db_adapter = db_adapter_instance or db_adapter

    async def list_all(self) -> List[ScannerToolSettings]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            r = await session.execute(select(ScannerToolSettingsModel))
            return [_model_to_entity(m) for m in r.scalars().all()]

    async def get_by_key(self, scanner_key: str) -> Optional[ScannerToolSettings]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            r = await session.execute(
                select(ScannerToolSettingsModel).where(
                    ScannerToolSettingsModel.scanner_key == scanner_key
                )
            )
            m = r.scalar_one_or_none()
            return _model_to_entity(m) if m else None

    async def save(self, settings: ScannerToolSettings) -> ScannerToolSettings:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            r = await session.execute(
                select(ScannerToolSettingsModel).where(
                    ScannerToolSettingsModel.scanner_key == settings.scanner_key
                )
            )
            m = r.scalar_one_or_none()
            now = datetime.utcnow()
            if m:
                m.enabled = settings.enabled
                m.timeout_seconds = settings.timeout_seconds
                m.config = settings.config
                m.updated_at = now
                m.updated_by_user_id = UUID(settings.updated_by_user_id) if settings.updated_by_user_id else None
            else:
                m = ScannerToolSettingsModel(
                    scanner_key=settings.scanner_key,
                    enabled=settings.enabled,
                    timeout_seconds=settings.timeout_seconds,
                    config=settings.config,
                    updated_by_user_id=UUID(settings.updated_by_user_id) if settings.updated_by_user_id else None,
                )
                session.add(m)
            await session.commit()
            await session.refresh(m)
            return _model_to_entity(m)

    async def delete_by_key(self, scanner_key: str) -> bool:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            r = await session.execute(
                select(ScannerToolSettingsModel).where(
                    ScannerToolSettingsModel.scanner_key == scanner_key
                )
            )
            m = r.scalar_one_or_none()
            if not m:
                return False
            await session.delete(m)
            await session.commit()
            return True
