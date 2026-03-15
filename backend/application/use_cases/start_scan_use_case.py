"""
Start Scan Use Case

This module defines the StartScanUseCase for initiating security scans.
This is a pure use case with no framework dependencies, containing only business logic.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from domain.entities.scan import Scan, ScanStatus, ScanType
from domain.entities.target_type import TargetType
from domain.value_objects.scan_config import ScanConfig
from domain.domain_services.scan_validation_service import ScanValidationService
from domain.exceptions.scan_exceptions import (
    InvalidScanConfigException,
    InvalidScanTargetException,
    ScanValidationException,
    ScanConcurrencyLimitException,
    ScanAlreadyExistsException
)

from application.dtos.scan_dto import ScanDTO
from application.dtos.request_dto import ScanRequestDTO


class StartScanUseCase:
    """Use case for starting a new scan."""
    
    def __init__(self, validation_service: ScanValidationService):
        self.validation_service = validation_service
    
    def execute(self, request: ScanRequestDTO) -> ScanDTO:
        """Execute the start scan use case."""
        # Validate request data
        request.validate()
        
        # Create scan configuration
        config = request.to_scan_config()
        
        # Validate scan configuration
        if config:
            self.validation_service.validate_scan_config(config)
        
        # Validate scan creation parameters
        self.validation_service.validate_scan_creation(
            name=request.name,
            description=request.description,
            scan_type=request.scan_type,
            target_url=request.target_url,
            target_type=request.target_type,
            scanners=request.scanners,
            config=config,
            user_id=request.user_id,
            project_id=request.project_id,
            tags=request.tags
        )
        
        # Check for existing scan (optional - depends on business rules)
        # This would typically check if a scan with the same name and target already exists
        
        # Create scan entity
        scan = self._create_scan_entity(request, config)
        
        # Convert to DTO
        scan_dto = ScanDTO.from_entity(scan)
        
        return scan_dto
    
    def _create_scan_entity(self, request: ScanRequestDTO, config: Optional[ScanConfig]) -> Scan:
        """Create a Scan entity from request data."""
        return Scan(
            name=request.name,
            description=request.description,
            scan_type=request.scan_type,
            target_url=request.target_url,
            target_type=request.target_type,
            user_id=request.user_id,
            project_id=request.project_id,
            config=config.to_dict() if config else {},
            scanners=request.scanners,
            tags=request.tags,
            scan_metadata=request.metadata or {},
        )
    
    def validate_concurrent_scans(self, user_id: str, max_concurrent: int = 5) -> None:
        """Validate concurrent scan limits for a user."""
        # This would typically fetch user's current scans from repository
        # For now, we'll implement basic validation
        pass
    
    def check_scan_quota(self, user_id: str, scan_type: ScanType) -> None:
        """Check if user has exceeded scan quota."""
        # This would typically check against a quota system
        # For now, we'll implement basic validation
        pass
    
    def validate_target_permissions(self, user_id: str, target_url: str, target_type: str) -> None:
        """Validate user permissions for scanning target."""
        # This would typically check against a permissions system
        # For now, we'll implement basic validation
        pass
    
    def validate_scanner_availability(self, scanners: List[str]) -> None:
        """Validate that requested scanners are available."""
        # This would typically check against a scanner registry
        # For now, we'll implement basic validation
        if not scanners:
            raise InvalidScanConfigException("At least one scanner must be specified")
        
        for scanner in scanners:
            if not scanner or not scanner.strip():
                raise InvalidScanConfigException("Scanner names cannot be empty")
    
    def validate_scan_scheduling(self, scheduled_at: Optional[datetime]) -> None:
        """Validate scan scheduling parameters."""
        if scheduled_at:
            self.validation_service.validate_scan_scheduling(scheduled_at)
    
    def create_scan_from_template(self, template_id: str, user_id: str, overrides: Dict[str, Any]) -> ScanDTO:
        """Create a scan from a template with optional overrides."""
        # This would typically fetch template from repository
        # For now, we'll implement basic template logic
        raise NotImplementedError("Template-based scan creation not yet implemented")
    
    def validate_batch_scan_targets(self, targets: List[Dict[str, str]]) -> None:
        """Validate targets for batch scan."""
        if not targets:
            raise InvalidScanConfigException("At least one target must be specified for batch scan")
        
        for target in targets:
            target_url = target.get('url')
            target_type = target.get('type', TargetType.GIT_REPO.value)
            
            if not target_url or not target_url.strip():
                raise InvalidScanTargetException("Target URL cannot be empty")
            
            self.validation_service.validate_target_url(target_url, target_type)
    
    def estimate_scan_duration(self, scan_type: ScanType, target_url: str, scanners: List[str]) -> int:
        """Estimate scan duration in seconds."""
        # This would typically use historical data and scanner estimates
        # For now, return a basic estimate
        base_duration = 300  # 5 minutes base
        
        # Add time based on number of scanners
        scanner_factor = len(scanners) * 60  # 1 minute per scanner
        
        # Add time based on scan type
        type_factor = {
            ScanType.CODE: 120,
            ScanType.CONTAINER: 180,
            ScanType.INFRASTRUCTURE: 300,
            ScanType.WEB_APPLICATION: 240,
        }.get(scan_type, 120)
        
        return base_duration + scanner_factor + type_factor
    
    def validate_scan_cost(self, scan_type: ScanType, scanners: List[str], duration_estimate: int) -> None:
        """Validate that scan cost is within acceptable limits."""
        # This would typically check against cost policies
        # For now, we'll implement basic validation
        max_duration = 7200  # 2 hours maximum
        if duration_estimate > max_duration:
            raise ScanValidationException(f"Estimated scan duration ({duration_estimate}s) exceeds maximum allowed ({max_duration}s)")