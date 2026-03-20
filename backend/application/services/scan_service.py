"""
Scan Service

This module defines the ScanService for orchestrating scan operations.
This service coordinates between use cases, repositories, and infrastructure.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from domain.entities.scan import Scan, ScanStatus, ScanType
from domain.datetime_serialization import isoformat_utc
from domain.value_objects.scan_config import ScanConfig
from domain.services.scan_validation_service import ScanValidationService
from domain.services.scanner_duration_service import ScannerDurationService
from domain.exceptions.scan_exceptions import (
    ScanException,
    ScanNotFoundException,
    ScanValidationException,
)
from application.services.scan_enforcement import enforce_scan_creation
from domain.policies.finding_policy import (
    DEFAULT_FINDING_POLICY_APPLY_BY_DEFAULT,
    DEFAULT_FINDING_POLICY_PATH,
)
from domain.policies.scan_profile_policy import (
    extract_profile_catalog_from_scanner_metadata,
    is_scan_profile_allowed,
    normalize_profile_key,
    resolve_max_allowed_scan_profile_for_actor,
    resolve_profile_order,
    resolve_scan_profile_for_actor,
    scan_profile_settings,
)
from domain.exceptions.scan_exceptions import ScanPolicyBlockedException

from application.use_cases.start_scan_use_case import StartScanUseCase
from application.use_cases.process_result_use_case import ProcessResultUseCase
from application.use_cases.cancel_scan_use_case import CancelScanUseCase
from application.dtos.scan_dto import ScanDTO, ScanSummaryDTO, ScanStatisticsDTO
from application.dtos.request_dto import (
    ScanRequestDTO,
    ScanUpdateRequestDTO,
    ScanFilterDTO,
    CancelScanRequestDTO
)
from domain.utils.git_repo_url import normalize_repo_url_for_target_type


logger = logging.getLogger(__name__)


class ScanService:
    """Service for orchestrating scan operations."""
    
    def __init__(
        self,
        validation_service: ScanValidationService,
        scan_repository: Any,  # Would be ScanRepository interface
        queue_service: Any,    # Would be QueueService
        result_service: Any    # Would be ResultProcessingService
    ):
        self.validation_service = validation_service
        self.scan_repository = scan_repository
        self.queue_service = queue_service
        self.result_service = result_service
        
        # Initialize use cases
        self.start_scan_use_case = StartScanUseCase(validation_service)
        self.process_result_use_case = ProcessResultUseCase(validation_service)
        self.cancel_scan_use_case = CancelScanUseCase(validation_service)
    
    async def create_scan(
        self,
        request: ScanRequestDTO,
        *,
        actor_role: str = "user",
        guest_session_id: Optional[str] = None,
        enforcement_mode: str = "full",
    ) -> ScanDTO:
        """Create and start a new scan."""
        try:
            raw_target = (request.target_url or "").strip()
            normalized = normalize_repo_url_for_target_type(request.target_type, request.target_url or "")
            if normalized != raw_target:
                logger.info("Normalized git target URL: %s -> %s", raw_target, normalized)
            request.target_url = normalized
            await self._apply_default_finding_policy(request)
            await self._apply_default_scan_profile(request, actor_role=actor_role)
            await self._enforce_scan_profile_permissions(request, actor_role=actor_role)
            await enforce_scan_creation(
                self.scan_repository,
                request,
                actor_role=actor_role,
                guest_session_id=guest_session_id,
                enforcement_mode=enforcement_mode,
            )
            # Execute start scan use case
            scan_dto = self.start_scan_use_case.execute(request)
            
            # Save scan to repository
            scan_entity = await self._convert_dto_to_entity(scan_dto)
            saved_scan = await self.scan_repository.create(scan_entity)
            
            # Add to queue for processing
            await self.queue_service.enqueue_scan(saved_scan)
            
            # Convert back to DTO
            return ScanDTO.from_entity(saved_scan)
            
        except ScanException as e:
            raise e
        except Exception as e:
            raise ScanValidationException(f"Failed to create scan: {str(e)}")

    async def _apply_default_finding_policy(self, request: ScanRequestDTO) -> None:
        """
        Apply default finding policy path from SystemState scan_defaults when enabled.
        This runs for all creation paths (manual + auto + queued) because everything
        goes through ScanService.create_scan().
        """
        try:
            # Do not override explicit per-scan setting.
            cfg = dict(request.config or {})
            existing = cfg.get("finding_policy")
            if isinstance(existing, str) and existing.strip():
                return

            # Lazy import avoids circular import:
            # infrastructure.container imports ScanService at module import time.
            from infrastructure.container import get_system_state_repository
            repo = get_system_state_repository()
            state = await repo.get_singleton()
            defaults = ((state.config or {}).get("scan_defaults") or {}) if state else {}

            apply_default = bool(
                defaults.get(
                    "finding_policy_apply_by_default",
                    DEFAULT_FINDING_POLICY_APPLY_BY_DEFAULT,
                )
            )
            if not apply_default:
                return

            default_path = str(
                defaults.get("default_finding_policy_path", DEFAULT_FINDING_POLICY_PATH)
            ).strip()
            if not default_path:
                default_path = DEFAULT_FINDING_POLICY_PATH

            cfg["finding_policy"] = default_path
            request.config = cfg

            request.metadata = dict(request.metadata or {})
            request.metadata["finding_policy_default_applied"] = True
            request.metadata["finding_policy_path"] = default_path
        except Exception as e:
            # Non-fatal: scan creation should continue even if default lookup fails.
            logger.warning("Could not apply default finding policy path: %s", e)

    async def _apply_default_scan_profile(self, request: ScanRequestDTO, *, actor_role: str) -> None:
        """Apply role-based default scan_profile from SystemState scan_defaults."""
        try:
            cfg = dict(request.config or {})
            existing = cfg.get("scan_profile")
            if isinstance(existing, str) and existing.strip():
                return

            from infrastructure.container import get_system_state_repository
            repo = get_system_state_repository()
            state = await repo.get_singleton()

            settings = dict(scan_profile_settings())
            if state and state.config:
                settings.update((state.config or {}).get("scan_defaults") or {})

            selected = resolve_scan_profile_for_actor(
                settings,
                actor_role=actor_role,
                is_authenticated=bool(request.user_id),
            )
            cfg["scan_profile"] = selected
            request.config = cfg
        except Exception as e:
            logger.warning("Could not apply default scan profile: %s", e)

    async def _enforce_scan_profile_permissions(self, request: ScanRequestDTO, *, actor_role: str) -> None:
        """Enforce role-based max allowed scan profile."""
        cfg = dict(request.config or {})
        selected = cfg.get("scan_profile")
        if not isinstance(selected, str) or not selected.strip():
            return
        selected = normalize_profile_key(selected)

        from infrastructure.container import get_scanner_repository, get_system_state_repository
        scanner_repo = get_scanner_repository()
        scanners = await scanner_repo.list_all()
        catalog = extract_profile_catalog_from_scanner_metadata(scanners)
        if not catalog:
            raise ScanPolicyBlockedException("No scan profiles available. Scanner manifests define profiles.")
        if selected not in catalog:
            raise ScanPolicyBlockedException(f"Selected scan profile '{selected}' is not available.")

        repo = get_system_state_repository()
        state = await repo.get_singleton()
        settings = dict(scan_profile_settings())
        if state and state.config:
            settings.update((state.config or {}).get("scan_defaults") or {})
        profile_order = resolve_profile_order(settings, catalog=catalog)

        max_allowed = resolve_max_allowed_scan_profile_for_actor(
            settings,
            actor_role=actor_role,
            is_authenticated=bool(request.user_id),
        )
        if max_allowed not in profile_order:
            max_allowed = profile_order[-1]
        if not is_scan_profile_allowed(
            selected_profile=selected,
            max_allowed_profile=max_allowed,
            profile_order=profile_order,
        ):
            raise ScanPolicyBlockedException(
                f"Selected scan profile '{selected}' exceeds allowed maximum '{max_allowed}' for this actor."
            )
    
    async def get_scan_by_id(self, scan_id: str) -> ScanDTO:
        """Get scan by ID."""
        try:
            scan = await self.scan_repository.get_by_id(scan_id)
            if not scan:
                raise ScanNotFoundException(scan_id)
            
            return ScanDTO.from_entity(scan)
        except ScanException as e:
            raise e
    
    async def get_scan_status(self, scan_id: str) -> Dict[str, Any]:
        """Get scan status and progress."""
        try:
            scan = await self.scan_repository.get_by_id(scan_id)
            if not scan:
                raise ScanNotFoundException(scan_id)
            
            return {
                'scan_id': scan_id,
                'status': scan.status.value,
                'progress': self._calculate_scan_progress(scan),
                'started_at': isoformat_utc(scan.started_at),
                'completed_at': isoformat_utc(scan.completed_at),
                'duration': self._calculate_duration(scan),
                'vulnerabilities_found': scan.total_vulnerabilities,
                'metadata': scan.scan_metadata,
            }
        except ScanException as e:
            raise e
    
    async def list_scans(self, filter_dto: ScanFilterDTO) -> List[ScanSummaryDTO]:
        """List scans with filtering and pagination."""
        try:
            scans = await self.scan_repository.list_scans(
                user_id=filter_dto.user_id,
                guest_session_id=filter_dto.guest_session_id,
                project_id=filter_dto.project_id,
                status=ScanStatus(filter_dto.status) if filter_dto.status else None,
                scan_type=ScanType(filter_dto.scan_type) if filter_dto.scan_type else None,
                tags=filter_dto.tags,
                limit=filter_dto.limit,
                offset=filter_dto.offset,
            )
            
            return [ScanSummaryDTO.from_entity(scan) for scan in scans]
        except Exception as e:
            raise ScanValidationException(f"Failed to list scans: {str(e)}")
    
    async def update_scan(self, scan_id: str, update_request: ScanUpdateRequestDTO) -> ScanDTO:
        """Update scan information."""
        try:
            # Validate update request
            update_request.validate()
            
            # Get existing scan
            scan = await self.scan_repository.get_by_id(scan_id)
            if not scan:
                raise ScanNotFoundException(scan_id)
            
            # Update scan entity
            updated_scan = await self._update_scan_entity(scan, update_request)
            
            # Save updated scan
            saved_scan = await self.scan_repository.update(updated_scan)
            
            return ScanDTO.from_entity(saved_scan)
        except ScanException as e:
            raise e
    
    async def cancel_scan(self, request: CancelScanRequestDTO) -> ScanDTO:
        """Cancel a pending or running scan: load scan, set status cancelled, update DB, notify queue."""
        try:
            request.validate()
            scan = await self.scan_repository.get_by_id(request.scan_id)
            if not scan:
                raise ScanNotFoundException(request.scan_id)
            try:
                scan.cancel()
            except ValueError as e:
                raise ScanValidationException(str(e))
            if request.cancelled_by:
                scan.scan_metadata = scan.scan_metadata or {}
                scan.scan_metadata["cancelled_at"] = isoformat_utc(datetime.utcnow())
                scan.scan_metadata["cancelled_by"] = request.cancelled_by
                if request.reason:
                    scan.scan_metadata["cancellation_reason"] = request.reason
            updated_scan = await self.scan_repository.update(scan)
            await self.queue_service.cancel_scan(request.scan_id)
            return ScanDTO.from_entity(updated_scan)
        except ScanException as e:
            raise e
    
    async def delete_scan(self, scan_id: str) -> bool:
        """Delete a scan."""
        try:
            # Check if scan exists
            scan = await self.scan_repository.get_by_id(scan_id)
            if not scan:
                raise ScanNotFoundException(scan_id)
            
            # Delete from repository
            return await self.scan_repository.delete(scan_id)
        except ScanException as e:
            raise e
    
    async def get_scan_statistics(self, user_id: Optional[str] = None) -> ScanStatisticsDTO:
        """Get scan statistics."""
        try:
            stats = await self.scan_repository.get_scan_statistics(user_id)
            
            statistics_dto = ScanStatisticsDTO()
            statistics_dto.total_scans = stats.get('total_scans', 0)
            statistics_dto.pending_scans = stats.get('pending_scans', 0)
            statistics_dto.running_scans = stats.get('running_scans', 0)
            statistics_dto.completed_scans = stats.get('completed_scans', 0)
            statistics_dto.failed_scans = stats.get('failed_scans', 0)
            statistics_dto.cancelled_scans = stats.get('cancelled_scans', 0)
            
            statistics_dto.total_vulnerabilities = stats.get('total_vulnerabilities', 0)
            statistics_dto.critical_vulnerabilities = stats.get('critical_vulnerabilities', 0)
            statistics_dto.high_vulnerabilities = stats.get('high_vulnerabilities', 0)
            statistics_dto.medium_vulnerabilities = stats.get('medium_vulnerabilities', 0)
            statistics_dto.low_vulnerabilities = stats.get('low_vulnerabilities', 0)
            statistics_dto.info_vulnerabilities = stats.get('info_vulnerabilities', 0)
            
            statistics_dto.repository_scans = stats.get('repository_scans', 0)
            statistics_dto.container_scans = stats.get('container_scans', 0)
            statistics_dto.infrastructure_scans = stats.get('infrastructure_scans', 0)
            statistics_dto.web_application_scans = stats.get('web_application_scans', 0)
            
            statistics_dto.average_scan_duration = stats.get('average_scan_duration', 0.0)
            statistics_dto.longest_scan_duration = stats.get('longest_scan_duration', 0.0)
            statistics_dto.shortest_scan_duration = stats.get('shortest_scan_duration', 0.0)

            scanner_stats = await ScannerDurationService.get_all_stats()
            statistics_dto.scanner_duration_stats = scanner_stats

            return statistics_dto
        except Exception as e:
            raise ScanValidationException(f"Failed to get scan statistics: {str(e)}")
    
    async def retry_scan(self, scan_id: str) -> ScanDTO:
        """Retry a failed scan."""
        try:
            # Get existing scan
            scan = await self.scan_repository.get_by_id(scan_id)
            if not scan:
                raise ScanNotFoundException(scan_id)
            
            if scan.status not in (ScanStatus.FAILED, ScanStatus.INTERRUPTED):
                raise ScanValidationException(
                    "Only failed or interrupted scans can be retried"
                )
            
            # Create new scan request from existing scan
            request = self._create_retry_request(scan)
            
            # Create new scan
            return await self.create_scan(
                request,
                actor_role="user",
                guest_session_id=None,
                enforcement_mode="policies_only",
            )
        except ScanException as e:
            raise e
    
    async def get_recent_scans(
        self,
        limit: int = 10,
        *,
        owner_user_id: Optional[str] = None,
        guest_session_id: Optional[str] = None,
    ) -> List[ScanSummaryDTO]:
        """Recent scans for the current owner only."""
        try:
            scans = await self.scan_repository.get_recent_scans(
                limit,
                owner_user_id=owner_user_id,
                guest_session_id=guest_session_id,
            )
            return [ScanSummaryDTO.from_entity(scan) for scan in scans]
        except Exception as e:
            raise ScanValidationException(f"Failed to get recent scans: {str(e)}")
    
    async def add_tag(self, scan_id: str, tag: str) -> bool:
        """Add tag to scan."""
        try:
            return await self.scan_repository.add_tag(scan_id, tag)
        except Exception as e:
            raise ScanValidationException(f"Failed to add tag: {str(e)}")
    
    async def remove_tag(self, scan_id: str, tag: str) -> bool:
        """Remove tag from scan."""
        try:
            return await self.scan_repository.remove_tag(scan_id, tag)
        except Exception as e:
            raise ScanValidationException(f"Failed to remove tag: {str(e)}")
    
    def _calculate_scan_progress(self, scan: Scan) -> float:
        """Calculate scan progress percentage."""
        if scan.status == ScanStatus.COMPLETED:
            return 100.0
        elif scan.status == ScanStatus.PENDING:
            return 0.0
        elif scan.status == ScanStatus.RUNNING:
            # This would typically be calculated based on:
            # - Number of scanners completed vs total
            # - Scanner progress indicators
            # - Time elapsed vs estimated duration
            return 50.0  # Placeholder
        else:
            return 0.0
    
    def _calculate_duration(self, scan: Scan) -> Optional[float]:
        """Calculate scan duration in seconds."""
        if scan.started_at and scan.completed_at:
            return (scan.completed_at - scan.started_at).total_seconds()
        elif scan.started_at:
            return (datetime.utcnow() - scan.started_at).total_seconds()
        else:
            return None
    
    async def _convert_dto_to_entity(self, scan_dto: ScanDTO) -> Scan:
        """Convert ScanDTO to Scan entity."""
        return Scan(
            id=scan_dto.id,
            name=scan_dto.name,
            description=scan_dto.description,
            scan_type=scan_dto.scan_type,
            target_url=scan_dto.target_url,
            target_type=scan_dto.target_type,
            user_id=scan_dto.user_id,
            project_id=scan_dto.project_id,
            config=scan_dto.config,
            scanners=scan_dto.scanners,
            status=scan_dto.status,
            created_at=scan_dto.created_at,
            started_at=scan_dto.started_at,
            completed_at=scan_dto.completed_at,
            scheduled_at=scan_dto.scheduled_at,
            tags=scan_dto.tags,
            results=scan_dto.results,
            total_vulnerabilities=scan_dto.total_vulnerabilities,
            critical_vulnerabilities=scan_dto.critical_vulnerabilities,
            high_vulnerabilities=scan_dto.high_vulnerabilities,
            medium_vulnerabilities=scan_dto.medium_vulnerabilities,
            low_vulnerabilities=scan_dto.low_vulnerabilities,
            info_vulnerabilities=scan_dto.info_vulnerabilities,
            scan_metadata=scan_dto.metadata,
        )
    
    async def _update_scan_entity(self, scan: Scan, update_request: ScanUpdateRequestDTO) -> Scan:
        """Update scan entity with request data."""
        if update_request.name:
            scan.name = update_request.name
        if update_request.description is not None:
            scan.description = update_request.description
        if update_request.status:
            scan.status = ScanStatus(update_request.status)
        if update_request.config:
            scan.config = ScanConfig.from_dict(update_request.config)
        if update_request.tags is not None:
            scan.tags = update_request.tags
        if update_request.metadata is not None:
            scan.scan_metadata.update(update_request.metadata)
        
        return scan
    
    def _create_retry_request(self, scan: Scan) -> ScanRequestDTO:
        """Create retry request from existing scan."""
        return ScanRequestDTO(
            name=f"{scan.name} (Retry)",
            description=f"Retry of scan: {scan.description}",
            scan_type=scan.scan_type,
            target_url=scan.target_url,
            target_type=scan.target_type,
            user_id=scan.user_id,
            project_id=scan.project_id,
            config=scan.config.to_dict() if scan.config else None,
            scanners=scan.scanners,
            tags=scan.tags,
            metadata={**scan.scan_metadata, 'retry_of': scan.id},
        )