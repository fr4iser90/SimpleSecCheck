"""
Database Scan Repository Implementation

This module provides the PostgreSQL implementation of the ScanRepository interface.
"""
import json
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from domain.repositories.scan_repository import ScanRepository
from domain.entities.scan import Scan, ScanStatus, ScanType
from infrastructure.database.models import Scan as ScanModel
from infrastructure.database.adapter import db_adapter

logger = logging.getLogger(__name__)


class DatabaseScanRepository(ScanRepository):
    """PostgreSQL implementation of ScanRepository."""
    
    def __init__(self, db_adapter_instance=None):
        """Initialize repository with database adapter."""
        self.db_adapter = db_adapter_instance or db_adapter
    
    async def _entity_to_model(self, scan: Scan) -> ScanModel:
        """Convert Scan entity to database model."""
        return ScanModel(
            id=UUID(scan.id) if isinstance(scan.id, str) else scan.id,
            name=scan.name,
            description=scan.description,
            scan_type=scan.scan_type.value,
            status=scan.status.value,
            target_url=scan.target_url,
            target_type=scan.target_type,
            scanners=scan.scanners,
            config=scan.config,
            created_at=scan.created_at,
            started_at=scan.started_at,
            completed_at=scan.completed_at,
            updated_at=scan.updated_at,
            scheduled_at=scan.scheduled_at,
            last_heartbeat_at=scan.last_heartbeat_at,
            results=scan.results,
            total_vulnerabilities=scan.total_vulnerabilities,
            critical_vulnerabilities=scan.critical_vulnerabilities,
            high_vulnerabilities=scan.high_vulnerabilities,
            medium_vulnerabilities=scan.medium_vulnerabilities,
            low_vulnerabilities=scan.low_vulnerabilities,
            info_vulnerabilities=scan.info_vulnerabilities,
            duration=scan.duration,
            error_message=scan.error_message,
            retry_count=scan.retry_count,
            user_id=UUID(scan.user_id) if scan.user_id and isinstance(scan.user_id, str) else scan.user_id,
            project_id=scan.project_id,
            tags=scan.tags,
            scan_metadata=scan.scan_metadata,
            priority=scan.priority,
        )
    
    async def _model_to_entity(self, model: ScanModel) -> Scan:
        """Convert database model to Scan entity."""
        return Scan(
            id=str(model.id),
            name=model.name,
            description=model.description,
            scan_type=ScanType(model.scan_type),
            status=ScanStatus(model.status),
            target_url=model.target_url,
            target_type=model.target_type,
            scanners=model.scanners or [],
            config=model.config or {},
            created_at=model.created_at,
            started_at=model.started_at,
            completed_at=model.completed_at,
            updated_at=model.updated_at,
            scheduled_at=model.scheduled_at,
            last_heartbeat_at=model.last_heartbeat_at,
            results=model.results or [],
            total_vulnerabilities=model.total_vulnerabilities or 0,
            critical_vulnerabilities=model.critical_vulnerabilities or 0,
            high_vulnerabilities=model.high_vulnerabilities or 0,
            medium_vulnerabilities=model.medium_vulnerabilities or 0,
            low_vulnerabilities=model.low_vulnerabilities or 0,
            info_vulnerabilities=model.info_vulnerabilities or 0,
            duration=model.duration,
            error_message=model.error_message,
            retry_count=model.retry_count or 0,
            user_id=str(model.user_id) if model.user_id else None,
            project_id=model.project_id,
            tags=model.tags or [],
            scan_metadata=model.scan_metadata or {},
            priority=model.priority or 0,
        )
    
    async def create(self, scan: Scan) -> Scan:
        """Create a new scan in the database."""
        await self.db_adapter.ensure_initialized()
        
        async with self.db_adapter.async_session() as session:
            try:
                scan_model = await self._entity_to_model(scan)
                session.add(scan_model)
                await session.commit()
                await session.refresh(scan_model)
                
                logger.info(f"Created scan {scan.id} in database")
                return await self._model_to_entity(scan_model)
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to create scan {scan.id}: {e}")
                raise
    
    async def get_by_id(self, scan_id: str) -> Optional[Scan]:
        """Get scan by ID."""
        await self.db_adapter.ensure_initialized()
        
        async with self.db_adapter.async_session() as session:
            try:
                result = await session.execute(
                    select(ScanModel).where(ScanModel.id == UUID(scan_id))
                )
                model = result.scalar_one_or_none()
                if model:
                    return await self._model_to_entity(model)
                return None
            except Exception as e:
                logger.error(f"Failed to get scan {scan_id}: {e}")
                raise
    
    async def get_by_user(self, user_id: str, limit: int = 100, offset: int = 0) -> List[Scan]:
        """Get scans by user."""
        await self.db_adapter.ensure_initialized()
        
        async with self.db_adapter.async_session() as session:
            try:
                result = await session.execute(
                    select(ScanModel)
                    .where(ScanModel.user_id == UUID(user_id))
                    .order_by(ScanModel.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
                models = result.scalars().all()
                return [await self._model_to_entity(model) for model in models]
            except Exception as e:
                logger.error(f"Failed to get scans for user {user_id}: {e}")
                raise
    
    async def get_by_project(self, project_id: str, limit: int = 100, offset: int = 0) -> List[Scan]:
        """Get scans by project."""
        await self.db_adapter.ensure_initialized()
        
        async with self.db_adapter.async_session() as session:
            try:
                result = await session.execute(
                    select(ScanModel)
                    .where(ScanModel.project_id == project_id)
                    .order_by(ScanModel.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
                models = result.scalars().all()
                return [await self._model_to_entity(model) for model in models]
            except Exception as e:
                logger.error(f"Failed to get scans for project {project_id}: {e}")
                raise
    
    async def get_by_status(self, status: ScanStatus, limit: int = 100, offset: int = 0) -> List[Scan]:
        """Get scans by status."""
        await self.db_adapter.ensure_initialized()
        
        async with self.db_adapter.async_session() as session:
            try:
                result = await session.execute(
                    select(ScanModel)
                    .where(ScanModel.status == status.value)
                    .order_by(ScanModel.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
                models = result.scalars().all()
                return [await self._model_to_entity(model) for model in models]
            except Exception as e:
                logger.error(f"Failed to get scans with status {status.value}: {e}")
                raise
    
    async def get_by_type(self, scan_type: ScanType, limit: int = 100, offset: int = 0) -> List[Scan]:
        """Get scans by type."""
        await self.db_adapter.ensure_initialized()
        
        async with self.db_adapter.async_session() as session:
            try:
                result = await session.execute(
                    select(ScanModel)
                    .where(ScanModel.scan_type == scan_type.value)
                    .order_by(ScanModel.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
                models = result.scalars().all()
                return [await self._model_to_entity(model) for model in models]
            except Exception as e:
                logger.error(f"Failed to get scans with type {scan_type.value}: {e}")
                raise
    
    async def update(self, scan: Scan) -> Scan:
        """Update scan in database."""
        await self.db_adapter.ensure_initialized()
        
        async with self.db_adapter.async_session() as session:
            try:
                result = await session.execute(
                    select(ScanModel).where(ScanModel.id == UUID(scan.id))
                )
                model = result.scalar_one_or_none()
                if not model:
                    raise ValueError(f"Scan {scan.id} not found")
                
                # Update all fields
                model.name = scan.name
                model.description = scan.description
                model.scan_type = scan.scan_type.value
                model.status = scan.status.value
                model.target_url = scan.target_url
                model.target_type = scan.target_type
                model.scanners = scan.scanners
                model.config = scan.config
                model.started_at = scan.started_at
                model.completed_at = scan.completed_at
                model.updated_at = scan.updated_at
                model.scheduled_at = scan.scheduled_at
                model.results = scan.results
                model.total_vulnerabilities = scan.total_vulnerabilities
                model.critical_vulnerabilities = scan.critical_vulnerabilities
                model.high_vulnerabilities = scan.high_vulnerabilities
                model.medium_vulnerabilities = scan.medium_vulnerabilities
                model.low_vulnerabilities = scan.low_vulnerabilities
                model.info_vulnerabilities = scan.info_vulnerabilities
                model.duration = scan.duration
                model.error_message = scan.error_message
                model.retry_count = scan.retry_count
                model.user_id = UUID(scan.user_id) if scan.user_id and isinstance(scan.user_id, str) else scan.user_id
                model.project_id = scan.project_id
                model.tags = scan.tags
                model.scan_metadata = scan.scan_metadata
                
                await session.commit()
                await session.refresh(model)
                
                logger.info(f"Updated scan {scan.id} in database")
                return await self._model_to_entity(model)
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to update scan {scan.id}: {e}")
                raise
    
    async def delete(self, scan_id: str) -> bool:
        """Delete scan from database."""
        await self.db_adapter.ensure_initialized()
        
        async with self.db_adapter.async_session() as session:
            try:
                result = await session.execute(
                    select(ScanModel).where(ScanModel.id == UUID(scan_id))
                )
                model = result.scalar_one_or_none()
                if not model:
                    return False
                
                await session.delete(model)
                await session.commit()
                
                logger.info(f"Deleted scan {scan_id} from database")
                return True
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to delete scan {scan_id}: {e}")
                raise
    
    async def list_scans(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        status: Optional[ScanStatus] = None,
        scan_type: Optional[ScanType] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Scan]:
        """List scans with optional filtering."""
        await self.db_adapter.ensure_initialized()
        
        async with self.db_adapter.async_session() as session:
            try:
                query = select(ScanModel)
                conditions = []
                
                if user_id:
                    conditions.append(ScanModel.user_id == UUID(user_id))
                if project_id:
                    conditions.append(ScanModel.project_id == project_id)
                if status:
                    conditions.append(ScanModel.status == status.value)
                if scan_type:
                    conditions.append(ScanModel.scan_type == scan_type.value)
                if tags:
                    # PostgreSQL JSONB contains operator
                    for tag in tags:
                        conditions.append(ScanModel.tags.contains([tag]))
                
                if conditions:
                    query = query.where(and_(*conditions))
                
                query = query.order_by(ScanModel.created_at.desc()).limit(limit).offset(offset)
                
                result = await session.execute(query)
                models = result.scalars().all()
                return [await self._model_to_entity(model) for model in models]
            except Exception as e:
                logger.error(f"Failed to list scans: {e}")
                raise
    
    async def count_scans(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        status: Optional[ScanStatus] = None,
        scan_type: Optional[ScanType] = None,
        tags: Optional[List[str]] = None
    ) -> int:
        """Count scans with optional filtering."""
        await self.db_adapter.ensure_initialized()
        
        async with self.db_adapter.async_session() as session:
            try:
                query = select(func.count(ScanModel.id))
                conditions = []
                
                if user_id:
                    conditions.append(ScanModel.user_id == UUID(user_id))
                if project_id:
                    conditions.append(ScanModel.project_id == project_id)
                if status:
                    conditions.append(ScanModel.status == status.value)
                if scan_type:
                    conditions.append(ScanModel.scan_type == scan_type.value)
                if tags:
                    for tag in tags:
                        conditions.append(ScanModel.tags.contains([tag]))
                
                if conditions:
                    query = query.where(and_(*conditions))
                
                result = await session.execute(query)
                return result.scalar() or 0
            except Exception as e:
                logger.error(f"Failed to count scans: {e}")
                raise
    
    async def add_tag(self, scan_id: str, tag: str) -> bool:
        """Add tag to scan."""
        await self.db_adapter.ensure_initialized()
        
        async with self.db_adapter.async_session() as session:
            try:
                result = await session.execute(
                    select(ScanModel).where(ScanModel.id == UUID(scan_id))
                )
                model = result.scalar_one_or_none()
                if not model:
                    return False
                
                tags = model.tags or []
                if tag not in tags:
                    tags.append(tag)
                    model.tags = tags
                    await session.commit()
                    return True
                return False
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to add tag to scan {scan_id}: {e}")
                raise
    
    async def remove_tag(self, scan_id: str, tag: str) -> bool:
        """Remove tag from scan."""
        await self.db_adapter.ensure_initialized()
        
        async with self.db_adapter.async_session() as session:
            try:
                result = await session.execute(
                    select(ScanModel).where(ScanModel.id == UUID(scan_id))
                )
                model = result.scalar_one_or_none()
                if not model:
                    return False
                
                tags = model.tags or []
                if tag in tags:
                    tags.remove(tag)
                    model.tags = tags
                    await session.commit()
                    return True
                return False
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to remove tag from scan {scan_id}: {e}")
                raise
    
    async def update_status(self, scan_id: str, status: ScanStatus) -> bool:
        """Update scan status."""
        await self.db_adapter.ensure_initialized()
        
        async with self.db_adapter.async_session() as session:
            try:
                result = await session.execute(
                    select(ScanModel).where(ScanModel.id == UUID(scan_id))
                )
                model = result.scalar_one_or_none()
                if not model:
                    return False
                
                model.status = status.value
                await session.commit()
                return True
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to update status for scan {scan_id}: {e}")
                raise
    
    async def update_results(self, scan_id: str, results: List[Dict[str, Any]]) -> bool:
        """Update scan results."""
        await self.db_adapter.ensure_initialized()
        
        async with self.db_adapter.async_session() as session:
            try:
                result = await session.execute(
                    select(ScanModel).where(ScanModel.id == UUID(scan_id))
                )
                model = result.scalar_one_or_none()
                if not model:
                    return False
                
                model.results = results
                await session.commit()
                
                # Update scanner duration statistics after successful commit
                try:
                    from domain.services.scanner_duration_service import ScannerDurationService
                    await ScannerDurationService.update_stats_from_scan_results(results)
                except Exception as stats_error:
                    # Don't fail the update if stats update fails
                    logger.warning(f"Failed to update scanner duration stats: {stats_error}")
                
                return True
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to update results for scan {scan_id}: {e}")
                raise
    
    async def get_recent_scans(self, limit: int = 10) -> List[Scan]:
        """Get recent scans."""
        await self.db_adapter.ensure_initialized()
        
        async with self.db_adapter.async_session() as session:
            try:
                result = await session.execute(
                    select(ScanModel)
                    .order_by(ScanModel.created_at.desc())
                    .limit(limit)
                )
                models = result.scalars().all()
                return [await self._model_to_entity(model) for model in models]
            except Exception as e:
                logger.error(f"Failed to get recent scans: {e}")
                raise
    
    async def get_scan_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get scan statistics for API (ScanStatisticsSchema)."""
        await self.db_adapter.ensure_initialized()
        
        async with self.db_adapter.async_session() as session:
            try:
                query = select(ScanModel)
                if user_id:
                    query = query.where(ScanModel.user_id == UUID(user_id))
                
                result = await session.execute(query)
                scans = result.scalars().all()
                
                by_status: Dict[str, int] = {}
                by_type: Dict[str, int] = {}
                total_vuln = 0
                critical = high = medium = low = info = 0
                durations: List[float] = []
                repo_scans = container_scans = infra_scans = web_scans = 0
                
                for scan in scans:
                    status = (scan.status or "pending").lower()
                    by_status[status] = by_status.get(status, 0) + 1
                    st = (scan.scan_type or "code").lower()
                    by_type[st] = by_type.get(st, 0) + 1
                    total_vuln += scan.total_vulnerabilities or 0
                    critical += scan.critical_vulnerabilities or 0
                    high += scan.high_vulnerabilities or 0
                    medium += scan.medium_vulnerabilities or 0
                    low += scan.low_vulnerabilities or 0
                    info += scan.info_vulnerabilities or 0
                    if getattr(scan, "duration", None) is not None:
                        durations.append(float(scan.duration))
                    if st in ("code", "repository", "repo"):
                        repo_scans += 1
                    elif st in ("image", "container"):
                        container_scans += 1
                    elif st in ("infrastructure", "infra", "terraform"):
                        infra_scans += 1
                    elif st in ("web", "web_application"):
                        web_scans += 1
                
                total = len(scans)
                avg_dur = sum(durations) / len(durations) if durations else 0.0
                return {
                    "total_scans": total,
                    "pending_scans": by_status.get("pending", 0),
                    "running_scans": by_status.get("running", 0),
                    "completed_scans": by_status.get("completed", 0),
                    "failed_scans": by_status.get("failed", 0),
                    "cancelled_scans": by_status.get("cancelled", 0),
                    "total_vulnerabilities": total_vuln,
                    "critical_vulnerabilities": critical,
                    "high_vulnerabilities": high,
                    "medium_vulnerabilities": medium,
                    "low_vulnerabilities": low,
                    "info_vulnerabilities": info,
                    "repository_scans": repo_scans,
                    "container_scans": container_scans,
                    "infrastructure_scans": infra_scans,
                    "web_application_scans": web_scans,
                    "average_scan_duration": avg_dur,
                    "longest_scan_duration": max(durations) if durations else 0.0,
                    "shortest_scan_duration": min(durations) if durations else 0.0,
                }
            except Exception as e:
                logger.error(f"Failed to get scan statistics: {e}")
                raise
