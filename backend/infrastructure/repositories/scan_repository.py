"""
Database Scan Repository Implementation

This module provides the PostgreSQL implementation of the ScanRepository interface.
"""
import json
import logging
import re
from datetime import datetime
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text, cast

from domain.repositories.scan_repository import ScanRepository
from domain.entities.scan import Scan, ScanStatus, ScanType
from infrastructure.database.models import Scan as ScanModel, ScanStatusEnumType
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
                    .where(ScanModel.status == cast(status.value, ScanStatusEnumType))
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
        guest_session_id: Optional[str] = None,
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
                extra_params: Dict[str, Any] = {}
                
                if guest_session_id:
                    conditions.append(text("scans.scan_metadata->>'session_id' = :gsid"))
                    extra_params["gsid"] = guest_session_id
                elif user_id:
                    conditions.append(ScanModel.user_id == UUID(user_id))
                if project_id:
                    conditions.append(ScanModel.project_id == project_id)
                if status:
                    conditions.append(ScanModel.status == cast(status.value, ScanStatusEnumType))
                if scan_type:
                    conditions.append(ScanModel.scan_type == scan_type.value)
                if tags:
                    for tag in tags:
                        conditions.append(ScanModel.tags.contains([tag]))
                
                if conditions:
                    query = query.where(and_(*conditions))
                
                query = query.order_by(ScanModel.created_at.desc()).limit(limit).offset(offset)
                result = await session.execute(
                    query.params(**extra_params) if extra_params else query
                )
                models = result.scalars().all()
                return [await self._model_to_entity(model) for model in models]
            except Exception as e:
                logger.error(f"Failed to list scans: {e}")
                raise
    
    async def count_scans(
        self,
        user_id: Optional[str] = None,
        guest_session_id: Optional[str] = None,
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
                extra_params: Dict[str, Any] = {}
                
                if guest_session_id:
                    conditions.append(text("scans.scan_metadata->>'session_id' = :gsid"))
                    extra_params["gsid"] = guest_session_id
                elif user_id:
                    conditions.append(ScanModel.user_id == UUID(user_id))
                if project_id:
                    conditions.append(ScanModel.project_id == project_id)
                if status:
                    conditions.append(ScanModel.status == cast(status.value, ScanStatusEnumType))
                if scan_type:
                    conditions.append(ScanModel.scan_type == scan_type.value)
                if tags:
                    for tag in tags:
                        conditions.append(ScanModel.tags.contains([tag]))
                
                if conditions:
                    query = query.where(and_(*conditions))
                
                result = await session.execute(
                    query.params(**extra_params) if extra_params else query
                )
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
    
    async def get_recent_scans(
        self,
        limit: int = 10,
        *,
        owner_user_id: Optional[str] = None,
        guest_session_id: Optional[str] = None,
    ) -> List[Scan]:
        """Recent scans for one owner; empty if no owner scope."""
        await self.db_adapter.ensure_initialized()
        
        async with self.db_adapter.async_session() as session:
            try:
                q = select(ScanModel)
                if guest_session_id:
                    q = (
                        q.where(text("scans.scan_metadata->>'session_id' = :gsid"))
                        .params(gsid=guest_session_id)
                    )
                elif owner_user_id:
                    q = q.where(ScanModel.user_id == UUID(owner_user_id))
                else:
                    return []
                q = q.order_by(ScanModel.created_at.desc()).limit(limit)
                result = await session.execute(q)
                models = result.scalars().all()
                return [await self._model_to_entity(model) for model in models]
            except Exception as e:
                logger.error(f"Failed to get recent scans: {e}")
                raise
    
    async def get_scan_statistics(
        self,
        user_id: Optional[str] = None,
        guest_session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get scan statistics for API (ScanStatisticsSchema)."""
        await self.db_adapter.ensure_initialized()
        
        async with self.db_adapter.async_session() as session:
            try:
                query = select(ScanModel)
                if user_id:
                    query = query.where(ScanModel.user_id == UUID(user_id))
                elif guest_session_id:
                    query = query.where(
                        and_(
                            ScanModel.user_id.is_(None),
                            text("scans.scan_metadata->>'session_id' = :gsid"),
                        )
                    ).params(gsid=guest_session_id)
                
                result = await session.execute(query)
                scans = result.scalars().all()
                
                by_status: Dict[str, int] = {}
                by_type: Dict[str, int] = {}
                total_vuln = 0
                critical = high = medium = low = info = 0
                durations: List[float] = []
                repo_scans = container_scans = infra_scans = web_scans = 0
                distinct_targets: set[str] = set()
                distinct_repositories: set[str] = set()
                distinct_repo_owners: set[str] = set()
                daily_rollup: Dict[str, Dict[str, int]] = {}

                def _extract_repo_owner_and_slug(raw_url: str) -> tuple[Optional[str], Optional[str]]:
                    if not raw_url:
                        return None, None
                    target = raw_url.strip()
                    if not target:
                        return None, None

                    # Handle SSH notation: git@github.com:owner/repo(.git)
                    ssh_match = re.match(r"^git@github\.com:([^/]+)/(.+)$", target, flags=re.IGNORECASE)
                    if ssh_match:
                        owner = ssh_match.group(1).strip().lower()
                        repo = ssh_match.group(2).strip()
                        if repo.lower().endswith(".git"):
                            repo = repo[:-4]
                        repo = repo.strip("/").lower()
                        if owner and repo:
                            return owner, f"{owner}/{repo}"
                        return owner or None, None

                    # Handle http(s) URLs
                    if "://" in target:
                        parsed = urlparse(target)
                        if parsed.netloc.lower() == "github.com":
                            parts = [p for p in parsed.path.split("/") if p]
                            if len(parts) >= 2:
                                owner = parts[0].strip().lower()
                                repo = parts[1].strip()
                                if repo.lower().endswith(".git"):
                                    repo = repo[:-4]
                                repo = repo.lower()
                                if owner and repo:
                                    return owner, f"{owner}/{repo}"
                                return owner or None, None
                    return None, None
                
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
                    if scan.target_url:
                        distinct_targets.add(f"{(scan.target_type or '').lower()}::{scan.target_url.strip().lower()}")
                    if st in ("code", "repository", "repo"):
                        repo_scans += 1
                        owner, slug = _extract_repo_owner_and_slug(scan.target_url or "")
                        if owner:
                            distinct_repo_owners.add(owner)
                        if slug:
                            distinct_repositories.add(slug)
                    elif st in ("image", "container"):
                        container_scans += 1
                    elif st in ("infrastructure", "infra", "terraform"):
                        infra_scans += 1
                    elif st in ("web", "web_application"):
                        web_scans += 1

                    if scan.created_at:
                        day_key = scan.created_at.strftime("%Y-%m-%d")
                        if day_key not in daily_rollup:
                            daily_rollup[day_key] = {
                                "total_scans": 0,
                                "repository_scans": 0,
                                "container_scans": 0,
                                "infrastructure_scans": 0,
                                "web_application_scans": 0,
                            }
                        day_bucket = daily_rollup[day_key]
                        day_bucket["total_scans"] += 1
                        if st in ("code", "repository", "repo"):
                            day_bucket["repository_scans"] += 1
                        elif st in ("image", "container"):
                            day_bucket["container_scans"] += 1
                        elif st in ("infrastructure", "infra", "terraform"):
                            day_bucket["infrastructure_scans"] += 1
                        elif st in ("web", "web_application"):
                            day_bucket["web_application_scans"] += 1
                
                total = len(scans)
                avg_dur = sum(durations) / len(durations) if durations else 0.0
                daily_scan_counts = [
                    {"date": day, **counts}
                    for day, counts in sorted(daily_rollup.items(), key=lambda item: item[0])
                ]
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
                    "distinct_targets_scanned": len(distinct_targets),
                    "distinct_repositories_scanned": len(distinct_repositories),
                    "distinct_repo_owners_scanned": len(distinct_repo_owners),
                    "average_scan_duration": avg_dur,
                    "longest_scan_duration": max(durations) if durations else 0.0,
                    "shortest_scan_duration": min(durations) if durations else 0.0,
                    "daily_scan_counts": daily_scan_counts,
                }
            except Exception as e:
                logger.error(f"Failed to get scan statistics: {e}")
                raise

    async def count_scans_created_since(
        self,
        since: datetime,
        *,
        global_all: bool = False,
        user_id: Optional[str] = None,
        guest_session_id: Optional[str] = None,
    ) -> int:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            try:
                query = select(func.count(ScanModel.id)).where(ScanModel.created_at >= since)
                extra_params: Dict[str, Any] = {}
                if global_all:
                    pass
                elif user_id:
                    query = query.where(ScanModel.user_id == UUID(user_id))
                elif guest_session_id:
                    query = query.where(
                        and_(
                            ScanModel.user_id.is_(None),
                            text("scans.scan_metadata->>'session_id' = :gsid"),
                        )
                    )
                    extra_params["gsid"] = guest_session_id
                else:
                    return 0
                result = await session.execute(
                    query.params(**extra_params) if extra_params else query
                )
                return int(result.scalar() or 0)
            except Exception as e:
                logger.error(f"count_scans_created_since failed: {e}")
                raise

    async def count_active_scans_for_actor(
        self,
        *,
        user_id: Optional[str] = None,
        guest_session_id: Optional[str] = None,
    ) -> int:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            try:
                st = or_(
                    ScanModel.status == cast(ScanStatus.PENDING.value, ScanStatusEnumType),
                    ScanModel.status == cast(ScanStatus.RUNNING.value, ScanStatusEnumType),
                )
                query = select(func.count(ScanModel.id)).where(st)
                extra_params: Dict[str, Any] = {}
                if user_id:
                    query = query.where(ScanModel.user_id == UUID(user_id))
                elif guest_session_id:
                    query = query.where(
                        and_(
                            ScanModel.user_id.is_(None),
                            text("scans.scan_metadata->>'session_id' = :gsid"),
                        )
                    )
                    extra_params["gsid"] = guest_session_id
                else:
                    return 0
                result = await session.execute(
                    query.params(**extra_params) if extra_params else query
                )
                return int(result.scalar() or 0)
            except Exception as e:
                logger.error(f"count_active_scans_for_actor failed: {e}")
                raise

    async def find_active_scan_by_user_and_target(
        self, user_id: str, target_url_contains: str
    ) -> Optional[Scan]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            try:
                result = await session.execute(
                    select(ScanModel)
                    .where(
                        and_(
                            ScanModel.user_id == UUID(user_id),
                            ScanModel.status.in_(["pending", "running"]),
                            ScanModel.target_url.contains(target_url_contains),
                        )
                    )
                    .order_by(ScanModel.created_at.desc())
                    .limit(1)
                )
                model = result.scalar_one_or_none()
                return await self._model_to_entity(model) if model else None
            except Exception as e:
                logger.error(f"find_active_scan_by_user_and_target failed: {e}")
                raise

    async def find_latest_finished_scan_by_user_and_target(
        self, user_id: str, target_url: str
    ) -> Optional[Scan]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            try:
                result = await session.execute(
                    select(ScanModel)
                    .where(
                        and_(
                            ScanModel.user_id == UUID(user_id),
                            ScanModel.target_url == target_url,
                            ScanModel.status.in_(
                                ["completed", "failed", "cancelled", "interrupted"]
                            ),
                        )
                    )
                    .order_by(ScanModel.created_at.desc())
                    .limit(1)
                )
                model = result.scalar_one_or_none()
                return await self._model_to_entity(model) if model else None
            except Exception as e:
                logger.error(
                    f"find_latest_finished_scan_by_user_and_target failed: {e}"
                )
                raise

    async def get_queue_position(self, scan_id: str, user_id: str) -> Optional[int]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            try:
                scan_result = await session.execute(
                    select(ScanModel).where(
                        ScanModel.id == UUID(scan_id),
                        ScanModel.user_id == UUID(user_id),
                    )
                )
                scan = scan_result.scalar_one_or_none()
                if not scan or scan.status != "pending":
                    return None
                position_query = select(func.count(ScanModel.id)).where(
                    and_(
                        ScanModel.status == cast("pending", ScanStatusEnumType),
                        ScanModel.user_id == UUID(user_id),
                        or_(
                            ScanModel.priority > scan.priority,
                            and_(
                                ScanModel.priority == scan.priority,
                                ScanModel.created_at < scan.created_at,
                            ),
                        ),
                    )
                )
                pos_result = await session.execute(position_query)
                return (pos_result.scalar() or 0) + 1
            except Exception as e:
                logger.error(f"get_queue_position failed: {e}")
                raise

    async def get_queue_items(
        self,
        status_filter: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Scan]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            try:
                query = select(ScanModel)
                if status_filter:
                    query = query.where(ScanModel.status.ilike(f"%{status_filter}%"))
                else:
                    query = query.where(ScanModel.status.in_(["pending", "running"]))
                query = (
                    query.order_by(ScanModel.priority.desc(), ScanModel.created_at.asc())
                    .limit(limit)
                    .offset(offset)
                )
                result = await session.execute(query)
                models = result.scalars().all()
                return [await self._model_to_entity(m) for m in models]
            except Exception as e:
                logger.error(f"get_queue_items failed: {e}")
                raise

    async def count_by_statuses(self, statuses: List[str]) -> int:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            try:
                result = await session.execute(
                    select(func.count(ScanModel.id)).where(ScanModel.status.in_(statuses))
                )
                return int(result.scalar() or 0)
            except Exception as e:
                logger.error(f"count_by_statuses failed: {e}")
                raise

    async def get_latest_scans_by_target_urls(
        self, user_id: str, target_urls: List[str]
    ) -> Dict[str, Scan]:
        if not target_urls:
            return {}
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            try:
                result = await session.execute(
                    select(ScanModel)
                    .where(
                        ScanModel.user_id == UUID(user_id),
                        ScanModel.target_url.in_(target_urls),
                    )
                    .order_by(ScanModel.created_at.desc())
                )
                rows = result.scalars().all()
                out: Dict[str, Scan] = {}
                for r in rows:
                    url = r.target_url or ""
                    if url not in out:
                        out[url] = await self._model_to_entity(r)
                return out
            except Exception as e:
                logger.error(f"get_latest_scans_by_target_urls failed: {e}")
                raise

    async def get_active_scans_by_target_urls(
        self, user_id: str, target_urls: List[str]
    ) -> Dict[str, Scan]:
        if not target_urls:
            return {}
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            try:
                result = await session.execute(
                    select(ScanModel)
                    .where(
                        ScanModel.user_id == UUID(user_id),
                        ScanModel.status.in_(["pending", "running"]),
                        ScanModel.target_url.in_(target_urls),
                    )
                    .order_by(ScanModel.created_at.desc())
                )
                rows = result.scalars().all()
                out: Dict[str, Scan] = {}
                for r in rows:
                    url = r.target_url or ""
                    if url not in out:
                        out[url] = await self._model_to_entity(r)
                return out
            except Exception as e:
                logger.error(f"get_active_scans_by_target_urls failed: {e}")
                raise

    async def get_position_in_queue(self, scan_id: str) -> Optional[int]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            try:
                scan_result = await session.execute(
                    select(ScanModel).where(ScanModel.id == UUID(scan_id))
                )
                scan = scan_result.scalar_one_or_none()
                if not scan or scan.status not in ("pending", "running"):
                    return None
                position_query = select(func.count(ScanModel.id)).where(
                    and_(
                        ScanModel.status.in_(["pending", "running"]),
                        or_(
                            ScanModel.priority > scan.priority,
                            and_(
                                ScanModel.priority == scan.priority,
                                ScanModel.created_at < scan.created_at,
                            ),
                        ),
                    )
                )
                pos_result = await session.execute(position_query)
                return (pos_result.scalar() or 0) + 1
            except Exception as e:
                logger.error(f"get_position_in_queue failed: {e}")
                raise

    async def list_scans_for_actor(
        self,
        user_id: Optional[str] = None,
        guest_session_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 100,
    ) -> List[Scan]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            try:
                query = select(ScanModel)
                if guest_session_id:
                    query = query.where(
                        text("scans.scan_metadata->>'session_id' = :gsid")
                    ).params(gsid=guest_session_id)
                elif user_id:
                    query = query.where(ScanModel.user_id == UUID(user_id))
                else:
                    return []
                if status_filter:
                    query = query.where(ScanModel.status.ilike(f"%{status_filter}%"))
                query = (
                    query.order_by(ScanModel.priority.desc(), ScanModel.created_at.desc())
                    .limit(limit)
                )
                result = await session.execute(query)
                models = result.scalars().all()
                return [await self._model_to_entity(m) for m in models]
            except Exception as e:
                logger.error(f"list_scans_for_actor failed: {e}")
                raise

    async def get_scans_before_in_queue(self, scan_id: str) -> List[Scan]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            try:
                scan_result = await session.execute(
                    select(ScanModel).where(ScanModel.id == UUID(scan_id))
                )
                scan = scan_result.scalar_one_or_none()
                if not scan or scan.status not in ("pending", "running"):
                    return []
                before_query = (
                    select(ScanModel)
                    .where(ScanModel.status.in_(["pending", "running"]))
                    .where(
                        or_(
                            ScanModel.priority > scan.priority,
                            and_(
                                ScanModel.priority == scan.priority,
                                ScanModel.created_at < scan.created_at,
                            ),
                        )
                    )
                    .order_by(ScanModel.priority.desc(), ScanModel.created_at.asc())
                )
                result = await session.execute(before_query)
                models = result.scalars().all()
                return [await self._model_to_entity(m) for m in models]
            except Exception as e:
                logger.error(f"get_scans_before_in_queue failed: {e}")
                raise

    async def get_running_scans(self, limit: int = 50) -> List[Scan]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            try:
                result = await session.execute(
                    select(ScanModel)
                    .where(ScanModel.status == cast("running", ScanStatusEnumType))
                    .order_by(ScanModel.started_at.asc())
                    .limit(limit)
                )
                return [await self._model_to_entity(m) for m in result.scalars().all()]
            except Exception as e:
                logger.error(f"get_running_scans failed: {e}")
                raise

    async def count_today_by_filters(
        self,
        status: Optional[str] = None,
        error_message_contains: Optional[str] = None,
    ) -> int:
        await self.db_adapter.ensure_initialized()
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        async with self.db_adapter.async_session() as session:
            try:
                q = select(func.count(ScanModel.id)).where(ScanModel.created_at >= today)
                if status is not None:
                    q = q.where(ScanModel.status == cast(status, ScanStatusEnumType))
                if error_message_contains is not None:
                    q = q.where(ScanModel.error_message.ilike(f"%{error_message_contains}%"))
                r = await session.execute(q)
                return int(r.scalar() or 0)
            except Exception as e:
                logger.error(f"count_today_by_filters failed: {e}")
                raise

    async def get_avg_duration_completed_today(self) -> Optional[float]:
        await self.db_adapter.ensure_initialized()
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        async with self.db_adapter.async_session() as session:
            try:
                r = await session.execute(
                    select(func.avg(ScanModel.duration)).where(
                        and_(
                            ScanModel.created_at >= today,
                            ScanModel.status == cast("completed", ScanStatusEnumType),
                            ScanModel.duration.isnot(None),
                        )
                    )
                )
                v = r.scalar()
                return float(v) if v is not None else None
            except Exception as e:
                logger.error(f"get_avg_duration_completed_today failed: {e}")
                raise

    async def get_stale_running_scan_ids(
        self,
        stale_cutoff: datetime,
        null_cutoff: datetime,
        limit: int = 200,
    ) -> List[str]:
        await self.db_adapter.ensure_initialized()
        async with self.db_adapter.async_session() as session:
            try:
                from sqlalchemy import or_
                q = (
                    select(ScanModel.id)
                    .where(ScanModel.status == cast("running", ScanStatusEnumType))
                    .where(
                        or_(
                            and_(
                                ScanModel.last_heartbeat_at.isnot(None),
                                ScanModel.last_heartbeat_at < stale_cutoff,
                            ),
                            and_(
                                ScanModel.last_heartbeat_at.is_(None),
                                ScanModel.started_at.isnot(None),
                                ScanModel.started_at < null_cutoff,
                            ),
                            and_(
                                ScanModel.last_heartbeat_at.is_(None),
                                ScanModel.started_at.is_(None),
                            ),
                        )
                    )
                    .limit(limit)
                )
                r = await session.execute(q)
                return [str(row[0]) for row in r.fetchall()]
            except Exception as e:
                logger.error("get_stale_running_scan_ids failed: %s", e)
                raise
