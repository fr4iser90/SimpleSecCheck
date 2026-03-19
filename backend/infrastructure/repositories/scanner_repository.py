"""Database Scanner repository (DDD)."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select

from domain.entities.scanner import Scanner
from domain.repositories.scanner_repository import ScannerRepository
from infrastructure.database.models import Scanner as ScannerModel
from infrastructure.database.adapter import db_adapter


def _model_to_entity(m: ScannerModel) -> Scanner:
    return Scanner(
        id=str(m.id),
        name=m.name or "",
        scan_types=list(m.scan_types) if m.scan_types else [],
        priority=int(m.priority or 0),
        requires_condition=m.requires_condition,
        enabled=bool(m.enabled),
        scanner_metadata=dict(m.scanner_metadata) if m.scanner_metadata else {},
        created_at=m.created_at or datetime.utcnow(),
        updated_at=m.updated_at or datetime.utcnow(),
        last_discovered_at=m.last_discovered_at,
    )


class DatabaseScannerRepository(ScannerRepository):
    """PostgreSQL implementation of ScannerRepository."""

    def __init__(self, db_adapter_instance=None):
        self.db_adapter = db_adapter_instance or db_adapter

    async def table_exists(self) -> bool:
        return await self.db_adapter.check_table_exists("scanners")

    async def list_all(self) -> List[Scanner]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            result = await session.execute(select(ScannerModel).order_by(ScannerModel.name))
            return [_model_to_entity(m) for m in result.scalars().all()]

    async def get_by_name(self, name: str) -> Optional[Scanner]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            result = await session.execute(select(ScannerModel).where(ScannerModel.name == name))
            m = result.scalar_one_or_none()
            return _model_to_entity(m) if m else None

    async def get_by_tools_key(self, tools_key: str) -> Optional[Scanner]:
        want = (tools_key or "").strip().lower()
        if not want:
            return None
        scanners = await self.list_all()
        for sc in scanners:
            tk = (sc.scanner_metadata or {}).get("tools_key")
            if tk and str(tk).strip().lower() == want:
                return sc
        return None

    async def create_or_update_from_dict(self, data: Dict[str, Any]) -> Scanner:
        await self.db_adapter.ensure_initialized()
        name = data.get("name") or ""
        async with self.db_adapter.async_session() as session:
            result = await session.execute(select(ScannerModel).where(ScannerModel.name == name))
            m = result.scalar_one_or_none()
            now = datetime.utcnow()
            if m:
                m.scan_types = data.get("scan_types", [])
                m.priority = int(data.get("priority", 0))
                m.requires_condition = data.get("requires_condition")
                m.enabled = bool(data.get("enabled", True))
                m.scanner_metadata = data.get("scanner_metadata") or {}
                m.last_discovered_at = now
                m.updated_at = now
            else:
                m = ScannerModel(
                    name=name,
                    scan_types=data.get("scan_types", []),
                    priority=int(data.get("priority", 0)),
                    requires_condition=data.get("requires_condition"),
                    enabled=bool(data.get("enabled", True)),
                    scanner_metadata=data.get("scanner_metadata") or {},
                    last_discovered_at=now,
                )
                session.add(m)
            await session.commit()
            await session.refresh(m)
            return _model_to_entity(m)

    async def sync_all(self, scanners_data: List[Dict[str, Any]]) -> None:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            for data in scanners_data:
                name = data.get("name") or ""
                result = await session.execute(select(ScannerModel).where(ScannerModel.name == name))
                m = result.scalar_one_or_none()
                now = datetime.utcnow()
                if m:
                    m.scan_types = data.get("scan_types", [])
                    m.priority = int(data.get("priority", 0))
                    m.requires_condition = data.get("requires_condition")
                    m.enabled = bool(data.get("enabled", True))
                    m.scanner_metadata = data.get("scanner_metadata") or {}
                    m.last_discovered_at = now
                    m.updated_at = now
                else:
                    m = ScannerModel(
                        name=name,
                        scan_types=data.get("scan_types", []),
                        priority=int(data.get("priority", 0)),
                        requires_condition=data.get("requires_condition"),
                        enabled=bool(data.get("enabled", True)),
                        scanner_metadata=data.get("scanner_metadata") or {},
                        last_discovered_at=now,
                    )
                    session.add(m)
            await session.commit()
