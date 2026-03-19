"""Database ScannerDurationStats repository implementation."""
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import select

from domain.repositories.scanner_duration_stats_repository import ScannerDurationStatsRepository
from infrastructure.database.models import ScannerDurationStats as ScannerDurationStatsModel
from infrastructure.database.adapter import db_adapter

MAX_SAMPLES = 100


class DatabaseScannerDurationStatsRepository(ScannerDurationStatsRepository):
    """PostgreSQL implementation of ScannerDurationStatsRepository."""

    def __init__(self, db_adapter_instance=None):
        self.db_adapter = db_adapter_instance or db_adapter

    async def record_sample(self, scanner_name: str, duration_seconds: int) -> None:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            r = await session.execute(
                select(ScannerDurationStatsModel).where(
                    ScannerDurationStatsModel.scanner_name == scanner_name
                )
            )
            stats = r.scalar_one_or_none()
            if stats:
                old_count = min(stats.sample_count, MAX_SAMPLES - 1)
                new_count = old_count + 1
                new_avg = int((stats.avg_duration_seconds * old_count + duration_seconds) / new_count)
                stats.avg_duration_seconds = new_avg
                stats.sample_count = stats.sample_count + 1
                if stats.min_duration_seconds is None or duration_seconds < stats.min_duration_seconds:
                    stats.min_duration_seconds = duration_seconds
                if stats.max_duration_seconds is None or duration_seconds > stats.max_duration_seconds:
                    stats.max_duration_seconds = duration_seconds
                stats.last_updated = datetime.utcnow()
            else:
                s = ScannerDurationStatsModel(
                    scanner_name=scanner_name,
                    avg_duration_seconds=duration_seconds,
                    min_duration_seconds=duration_seconds,
                    max_duration_seconds=duration_seconds,
                    sample_count=1,
                )
                session.add(s)
            await session.commit()

    async def get_avg_by_scanner(self, scanner_name: str) -> Optional[int]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            r = await session.execute(
                select(ScannerDurationStatsModel).where(
                    ScannerDurationStatsModel.scanner_name == scanner_name
                )
            )
            s = r.scalar_one_or_none()
            if not s or s.sample_count <= 0:
                return None
            return s.avg_duration_seconds

    async def get_avgs_for_scanners(self, scanner_names: List[str]) -> Dict[str, int]:
        if not scanner_names:
            return {}
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            r = await session.execute(
                select(ScannerDurationStatsModel).where(
                    ScannerDurationStatsModel.scanner_name.in_(scanner_names),
                    ScannerDurationStatsModel.sample_count > 0,
                )
            )
            out = {}
            for s in r.scalars().all():
                out[s.scanner_name] = s.avg_duration_seconds
            return out

    async def get_all(self) -> List[Dict]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            r = await session.execute(select(ScannerDurationStatsModel))
            return [
                {
                    "scanner_name": s.scanner_name,
                    "avg_duration_seconds": s.avg_duration_seconds,
                    "min_duration_seconds": s.min_duration_seconds,
                    "max_duration_seconds": s.max_duration_seconds,
                    "sample_count": s.sample_count,
                    "last_updated": s.last_updated.isoformat() if s.last_updated else None,
                }
                for s in r.scalars().all()
            ]
