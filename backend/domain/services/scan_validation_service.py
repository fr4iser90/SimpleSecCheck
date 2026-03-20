"""
Scan Validation Service

This module defines the ScanValidationService for validating scan configurations and parameters.
This is a domain service that contains pure business logic without framework dependencies.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from domain.entities.scan import Scan, ScanStatus, ScanType
from domain.entities.target_type import TargetType
from domain.value_objects.scan_config import ScanConfig
from domain.exceptions.scan_exceptions import (
    InvalidScanConfigException,
    InvalidScanTargetException,
    ScanValidationException
)


class ScanValidationService:
    """Domain service for validating scan configurations and parameters."""
    
    def __init__(self):
        self._max_target_length = 2000
        self._max_description_length = 1000
        self._max_tags_count = 10
        self._max_tag_length = 50
        self._allowed_scan_types = [scan_type.value for scan_type in ScanType]
        # Allowed target types - dynamically generated from TargetType enum (single source of truth!)
        self._allowed_target_types = TargetType.get_all_values()
    
    def validate_scan_creation(
        self,
        name: str,
        description: str,
        scan_type: ScanType,
        target_url: str,
        target_type: str,
        scanners: List[str],
        config: Optional[ScanConfig] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> None:
        """Validate scan creation parameters."""
        # Validate name
        if not name or not name.strip():
            raise InvalidScanConfigException("Scan name cannot be empty")
        
        if len(name) > 200:
            raise InvalidScanConfigException("Scan name cannot exceed 200 characters")
        
        # Validate description
        if description and len(description) > self._max_description_length:
            raise InvalidScanConfigException(f"Description cannot exceed {self._max_description_length} characters")
        
        # Validate scan type
        if scan_type.value not in self._allowed_scan_types:
            raise InvalidScanConfigException(f"Invalid scan type: {scan_type}")
        
        # Validate target URL
        if not target_url or not target_url.strip():
            raise InvalidScanTargetException("Target URL cannot be empty")
        
        if len(target_url) > self._max_target_length:
            raise InvalidScanTargetException(f"Target URL cannot exceed {self._max_target_length} characters")
        
        # Validate target type
        if target_type not in self._allowed_target_types:
            raise InvalidScanTargetException(f"Invalid target type: {target_type}")
        
        # Validate target URL format for the given target type (e.g. uploaded_code requires upload_id)
        self.validate_target_url(target_url.strip(), target_type)
        
        # Validate scanners
        if not scanners:
            raise InvalidScanConfigException("At least one scanner must be specified")
        
        # Validate user and project IDs
        if user_id and len(user_id) > 100:
            raise InvalidScanConfigException("User ID cannot exceed 100 characters")
        
        if project_id and len(project_id) > 100:
            raise InvalidScanConfigException("Project ID cannot exceed 100 characters")
        
        # Validate tags
        if tags:
            if len(tags) > self._max_tags_count:
                raise InvalidScanConfigException(f"Cannot have more than {self._max_tags_count} tags")
            
            for tag in tags:
                if not tag or not tag.strip():
                    raise InvalidScanConfigException("Tags cannot be empty")
                
                if len(tag) > self._max_tag_length:
                    raise InvalidScanConfigException(f"Tag cannot exceed {self._max_tag_length} characters")
        
        # Validate scan config
        if config:
            try:
                config.validate()
            except ValueError as e:
                raise InvalidScanConfigException(f"Invalid scan configuration: {str(e)}")
    
    def validate_scan_config(self, config: ScanConfig) -> None:
        """Validate scan configuration."""
        try:
            config.validate()
        except ValueError as e:
            raise InvalidScanConfigException(f"Invalid scan configuration: {str(e)}")
    
    def validate_target_url(self, target_url: str, target_type: str) -> None:
        """Validate target URL format based on target type."""
        if not target_url or not target_url.strip():
            raise InvalidScanTargetException("Target URL cannot be empty")
        
        target_url = target_url.strip()
        
        if target_type == TargetType.GIT_REPO.value:
            self._validate_repository_url(target_url)
        elif target_type == TargetType.UPLOADED_CODE.value:
            self._validate_uploaded_code_reference(target_url)
        elif target_type == 'container':
            self._validate_container_url(target_url)
        elif target_type == 'web_application':
            self._validate_web_url(target_url)
        elif target_type == 'infrastructure':
            self._validate_infrastructure_target(target_url)
    
    def validate_scan_status_transition(self, current_status: ScanStatus, new_status: ScanStatus) -> None:
        """Validate scan status transition."""
        valid_transitions = {
            ScanStatus.PENDING: [ScanStatus.RUNNING, ScanStatus.CANCELLED],
            ScanStatus.RUNNING: [
                ScanStatus.COMPLETED,
                ScanStatus.FAILED,
                ScanStatus.CANCELLED,
                ScanStatus.INTERRUPTED,
            ],
            ScanStatus.COMPLETED: [],
            ScanStatus.FAILED: [ScanStatus.PENDING],
            ScanStatus.INTERRUPTED: [ScanStatus.PENDING],
            ScanStatus.CANCELLED: [ScanStatus.PENDING],
        }
        
        if new_status not in valid_transitions.get(current_status, []):
            raise ScanValidationException(
                f"Invalid status transition from {current_status.value} to {new_status.value}"
            )
    
    def validate_scan_results(self, results: List[Dict[str, Any]]) -> None:
        """Validate scan results format."""
        if not isinstance(results, list):
            raise ScanValidationException("Scan results must be a list")
        
        for result in results:
            if not isinstance(result, dict):
                raise ScanValidationException("Each scan result must be a dictionary")
            
            if 'scanner' not in result:
                raise ScanValidationException("Scan result must contain 'scanner' field")
            
            if 'status' not in result:
                raise ScanValidationException("Scan result must contain 'status' field")
    
    def validate_scan_update(self, scan: Scan, update_data: Dict[str, Any]) -> None:
        """Validate scan update data."""
        # Validate status update
        if 'status' in update_data:
            new_status = ScanStatus(update_data['status'])
            self.validate_scan_status_transition(scan.status, new_status)
        
        # Validate other fields
        if 'name' in update_data and (not update_data['name'] or len(update_data['name']) > 200):
            raise InvalidScanConfigException("Scan name cannot be empty or exceed 200 characters")
        
        if 'description' in update_data and len(update_data['description'] or '') > self._max_description_length:
            raise InvalidScanConfigException(f"Description cannot exceed {self._max_description_length} characters")
    
    def validate_scan_scheduling(self, scan_time: Optional[datetime] = None) -> None:
        """Validate scan scheduling parameters."""
        if scan_time and scan_time < datetime.utcnow():
            raise ScanValidationException("Scheduled scan time cannot be in the past")
    
    def _validate_repository_url(self, url: str) -> None:
        """Validate repository URL format."""
        if not url.startswith(('http://', 'https://', 'git@', 'ssh://')):
            raise InvalidScanTargetException("Repository URL must be a valid Git URL")
    
    def _validate_container_url(self, url: str) -> None:
        """Validate container URL format."""
        if not (url.startswith(('docker://', 'registry://')) or ':' in url or '/' in url):
            raise InvalidScanTargetException("Container URL must be a valid container image reference")
    
    def _validate_web_url(self, url: str) -> None:
        """Validate web application URL format."""
        if not url.startswith(('http://', 'https://')):
            raise InvalidScanTargetException("Web application URL must start with http:// or https://")
    
    def _validate_uploaded_code_reference(self, target_url: str) -> None:
        """Validate target_url for uploaded_code: must be an upload reference (e.g. upload_id from upload API)."""
        import re
        # Accept UUID (with or without hyphens) or "upload:" prefix + id
        uuid_pattern = re.compile(
            r"^[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{12}$"
        )
        if target_url.startswith("upload:"):
            ref = target_url[7:].strip()
            if not ref:
                raise InvalidScanTargetException(
                    "For ZIP upload (uploaded_code), target must be a valid upload reference (e.g. upload_id from upload)."
                )
            if not uuid_pattern.match(ref) and not ref.replace("-", "").isalnum():
                raise InvalidScanTargetException(
                    "Upload reference must be a valid identifier (e.g. UUID)."
                )
        elif not uuid_pattern.match(target_url.strip()):
            raise InvalidScanTargetException(
                "For ZIP upload (uploaded_code), target must be the upload ID (UUID) returned by the upload API."
            )

    def _validate_infrastructure_target(self, target: str) -> None:
        """Validate infrastructure target format."""
        # Infrastructure targets can be IPs, hostnames, or CIDR ranges
        if not target or not target.strip():
            raise InvalidScanTargetException("Infrastructure target cannot be empty")
    
    def validate_scanner_compatibility(self, scanners: List[str], scan_type: ScanType, target_type: str) -> None:
        """Validate scanner compatibility with scan type and target type."""
        # This would typically check against a registry of available scanners
        # For now, we'll do basic validation
        if not scanners:
            raise InvalidScanConfigException("At least one scanner must be specified")
        
        # Validate scanner names
        for scanner in scanners:
            if not scanner or not scanner.strip():
                raise InvalidScanConfigException("Scanner names cannot be empty")
            
            if len(scanner) > 100:
                raise InvalidScanConfigException("Scanner name cannot exceed 100 characters")
    
    def validate_concurrent_scans(self, user_scans: List[Scan], max_concurrent: int = 5) -> None:
        """Validate concurrent scan limits for a user."""
        running_scans = [scan for scan in user_scans if scan.status == ScanStatus.RUNNING]
        
        if len(running_scans) >= max_concurrent:
            raise ScanValidationException(f"Maximum number of concurrent scans ({max_concurrent}) exceeded")
    
    def validate_scan_permissions(
        self,
        user_id: str,
        project_id: Optional[str],
        target_url: str,
        target_type: str
    ) -> None:
        """Validate user permissions for scanning target."""
        # This would typically check against a permissions system
        # For now, we'll do basic validation
        if not user_id:
            raise ScanValidationException("User ID is required for scan permissions")
        
        if target_type == TargetType.GIT_REPO.value:
            # Would check if user has access to the repository
            pass
        elif target_type == 'web_application':
            # Would check if user has permission to scan the web application
            pass
        elif target_type == 'infrastructure':
            # Would check if user has permission to scan the infrastructure
            pass