"""
Cancel Scan Use Case

This module defines the CancelScanUseCase for cancelling running scans.
This is a pure use case with no framework dependencies, containing only business logic.
"""
from typing import Optional, Dict, Any
from datetime import datetime

from domain.entities.scan import Scan, ScanStatus
from domain.datetime_serialization import isoformat_utc
from domain.domain_services.scan_validation_service import ScanValidationService
from domain.exceptions.scan_exceptions import (
    ScanNotFoundException,
    ScanValidationException,
    ScanExecutionException
)

from application.dtos.scan_dto import ScanDTO
from application.dtos.request_dto import CancelScanRequestDTO


class CancelScanUseCase:
    """Use case for cancelling a running scan."""
    
    def __init__(self, validation_service: ScanValidationService):
        self.validation_service = validation_service
    
    def execute(self, request: CancelScanRequestDTO) -> ScanDTO:
        """Execute the cancel scan use case."""
        # Validate request data
        request.validate()
        
        # Validate scan status transition (would typically check current status)
        # For now, we'll assume the scan can be cancelled
        
        # Create cancelled scan entity
        scan = self._create_cancelled_scan_entity(request)
        
        # Convert to DTO
        scan_dto = ScanDTO.from_entity(scan)
        
        return scan_dto
    
    def _create_cancelled_scan_entity(self, request: CancelScanRequestDTO) -> Scan:
        """Create a cancelled scan entity."""
        # This would typically fetch the existing scan from repository
        # For now, we'll create a basic cancelled scan
        return Scan(
            name=f"Cancelled scan {request.scan_id}",
            description=f"Scan cancelled: {request.reason or 'No reason provided'}",
            scan_type=None,  # Would be fetched from existing scan
            target_url="unknown",  # Would be fetched from existing scan
            target_type="unknown",  # Would be fetched from existing scan
            user_id="unknown",  # Would be fetched from existing scan
            status=ScanStatus.CANCELLED,
            completed_at=datetime.utcnow(),
            metadata={
                'cancelled_by': 'user',
                'reason': request.reason,
                'force_cancelled': request.force,
                'cancelled_at': isoformat_utc(datetime.utcnow()),
            }
        )
    
    def validate_scan_cancellation(self, scan_id: str, force: bool = False) -> None:
        """Validate that a scan can be cancelled."""
        # This would typically check:
        # 1. Scan exists
        # 2. Scan is in a cancellable state (RUNNING, PENDING)
        # 3. User has permission to cancel
        # 4. Force cancellation rules
        
        if not scan_id:
            raise ScanValidationException("Scan ID cannot be empty")
        
        # Basic validation - would be enhanced with repository access
        if len(scan_id) < 10:
            raise ScanValidationException("Invalid scan ID format")
    
    def check_scan_dependencies(self, scan_id: str) -> bool:
        """Check if scan has dependencies that prevent cancellation."""
        # This would typically check for:
        # - Child scans or batch scans
        # - Running containers or processes
        # - External dependencies
        
        # For now, assume cancellation is allowed
        return True
    
    def cleanup_scan_resources(self, scan_id: str, force: bool = False) -> bool:
        """Clean up resources associated with the scan."""
        # This would typically:
        # 1. Stop running containers
        # 2. Kill running processes
        # 3. Clean up temporary files
        # 4. Release locks
        
        # For now, return success
        return True
    
    def notify_scan_cancellation(self, scan_id: str, reason: Optional[str] = None) -> None:
        """Notify relevant parties about scan cancellation."""
        # This would typically:
        # 1. Send notifications to users
        # 2. Update monitoring systems
        # 3. Log the cancellation event
        
        # For now, just log the action
        pass
    
    def handle_force_cancellation(self, scan_id: str) -> bool:
        """Handle force cancellation of a scan."""
        # Force cancellation would:
        # 1. Kill all associated processes
        # 2. Clean up resources aggressively
        # 3. May result in incomplete cleanup
        
        # For now, return success
        return True
    
    def validate_user_permissions(self, user_id: str, scan_id: str) -> bool:
        """Validate that user has permission to cancel the scan."""
        # This would typically check:
        # 1. User owns the scan
        # 2. User has admin permissions
        # 3. Scan is in shared project
        
        # For now, assume user has permission
        return True
    
    def get_scan_cancellation_policy(self, scan_id: str) -> Dict[str, Any]:
        """Get cancellation policy for a specific scan."""
        # This would typically return:
        # - Allowed cancellation states
        # - Required permissions
        # - Force cancellation rules
        # - Cleanup requirements
        
        return {
            'allowed_states': ['PENDING', 'RUNNING'],
            'requires_permission': True,
            'force_allowed': True,
            'cleanup_required': True,
        }
    
    def log_cancellation_attempt(self, scan_id: str, user_id: str, reason: Optional[str], force: bool) -> None:
        """Log scan cancellation attempt for audit purposes."""
        # This would typically log to:
        # 1. Audit log
        # 2. Security monitoring
        # 3. User activity log
        
        # For now, just pass
        pass
    
    def handle_batch_scan_cancellation(self, batch_scan_id: str, force: bool = False) -> bool:
        """Handle cancellation of a batch scan and all its child scans."""
        # This would typically:
        # 1. Find all child scans in the batch
        # 2. Cancel each child scan
        # 3. Update batch scan status
        # 4. Handle partial cancellations
        
        # For now, return success
        return True
    
    def validate_cancellation_timing(self, scan_id: str) -> bool:
        """Validate that cancellation is allowed at this time."""
        # This would typically check:
        # - Scan age (prevent cancellation of very old scans)
        # - System maintenance windows
        # - Business rules
        
        # For now, always allow
        return True