"""
Request DTO (Data Transfer Object)

This module defines DTOs for incoming request data validation and transfer.
These DTOs are used to validate and transfer data from API requests to application layer.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime

from domain.entities.scan import ScanType
from domain.entities.target_type import TargetType
from domain.value_objects.scan_config import ScanConfig


@dataclass
class ScanRequestDTO:
    """Data Transfer Object for scan creation requests."""
    
    # Basic scan information (non-default parameters first)
    name: str
    target_url: str
    user_id: str
    
    # Optional basic information
    description: Optional[str] = None
    scan_type: ScanType = ScanType.CODE
    target_type: str = TargetType.GIT_REPO.value
    project_id: Optional[str] = None
    
    # Scan configuration
    config: Optional[Dict[str, Any]] = None
    scanners: List[str] = field(default_factory=list)
    
    # Optional scheduling
    scheduled_at: Optional[datetime] = None
    
    # Tags and metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Queue priority (optional; if None, backend can set from role: admin=10, user=5, guest=1)
    priority: Optional[int] = None
    
    def validate(self) -> None:
        """Validate the scan request data."""
        if not self.name or not self.name.strip():
            raise ValueError("Scan name cannot be empty")
        
        if len(self.name) > 200:
            raise ValueError("Scan name cannot exceed 200 characters")
        
        if not self.target_url or not self.target_url.strip():
            raise ValueError("Target URL cannot be empty")
        
        if not self.scanners:
            raise ValueError("At least one scanner must be specified")
        
        if self.description and len(self.description) > 1000:
            raise ValueError("Description cannot exceed 1000 characters")
        
        if self.tags and len(self.tags) > 10:
            raise ValueError("Cannot have more than 10 tags")
        
        for tag in self.tags:
            if not tag or not tag.strip():
                raise ValueError("Tags cannot be empty")
            if len(tag) > 50:
                raise ValueError("Tag cannot exceed 50 characters")
    
    def to_scan_config(self) -> Optional[ScanConfig]:
        """Convert config dict to ScanConfig object."""
        if not self.config:
            return None
        
        return ScanConfig.from_dict(self.config)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for processing."""
        return {
            'name': self.name,
            'description': self.description,
            'scan_type': self.scan_type.value,
            'target_url': self.target_url,
            'target_type': self.target_type,
            'user_id': self.user_id,
            'project_id': self.project_id,
            'config': self.config,
            'scanners': self.scanners,
            'scheduled_at': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'tags': self.tags,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScanRequestDTO':
        """Create DTO from dictionary."""
        scheduled_at = None
        if data.get('scheduled_at'):
            scheduled_at = datetime.fromisoformat(data['scheduled_at'])
        
        return cls(
            name=data['name'],
            description=data.get('description'),
            scan_type=ScanType(data['scan_type']),
            target_url=data['target_url'],
            target_type=data.get('target_type', TargetType.GIT_REPO.value),
            user_id=data['user_id'],
            project_id=data.get('project_id'),
            config=data.get('config'),
            scanners=data.get('scanners', []),
            scheduled_at=scheduled_at,
            tags=data.get('tags', []),
            metadata=data.get('metadata', {}),
        )


@dataclass
class ScanUpdateRequestDTO:
    """Data Transfer Object for scan update requests."""
    
    # Optional fields that can be updated
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def validate(self) -> None:
        """Validate the scan update request data."""
        if self.name and (not self.name.strip() or len(self.name) > 200):
            raise ValueError("Scan name cannot be empty or exceed 200 characters")
        
        if self.description and len(self.description) > 1000:
            raise ValueError("Description cannot exceed 1000 characters")
        
        if self.tags and len(self.tags) > 10:
            raise ValueError("Cannot have more than 10 tags")
        
        for tag in self.tags or []:
            if not tag or not tag.strip():
                raise ValueError("Tags cannot be empty")
            if len(tag) > 50:
                raise ValueError("Tag cannot exceed 50 characters")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for processing."""
        return {
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'config': self.config,
            'tags': self.tags,
            'metadata': self.metadata,
        }


@dataclass
class ScanFilterDTO:
    """Data Transfer Object for scan filtering requests."""
    
    # Filter criteria
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    status: Optional[str] = None
    scan_type: Optional[str] = None
    tags: Optional[List[str]] = None
    
    # Pagination
    limit: int = 100
    offset: int = 0
    
    # Sorting
    sort_by: str = "created_at"
    sort_order: str = "desc"  # asc or desc
    
    def validate(self) -> None:
        """Validate the filter request data."""
        if self.limit <= 0 or self.limit > 1000:
            raise ValueError("Limit must be between 1 and 1000")
        
        if self.offset < 0:
            raise ValueError("Offset cannot be negative")
        
        if self.sort_order not in ['asc', 'desc']:
            raise ValueError("Sort order must be 'asc' or 'desc'")
        
        valid_sort_fields = ['created_at', 'started_at', 'completed_at', 'name', 'status', 'total_vulnerabilities']
        if self.sort_by not in valid_sort_fields:
            raise ValueError(f"Sort field must be one of: {', '.join(valid_sort_fields)}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for processing."""
        return {
            'user_id': self.user_id,
            'project_id': self.project_id,
            'status': self.status,
            'scan_type': self.scan_type,
            'tags': self.tags,
            'limit': self.limit,
            'offset': self.offset,
            'sort_by': self.sort_by,
            'sort_order': self.sort_order,
        }


@dataclass
class ResultRequestDTO:
    """Data Transfer Object for result processing requests."""
    
    # Scan information
    scan_id: str
    scanner: str
    
    # Result data
    status: str  # SUCCESS, FAILED, PARTIAL
    message: Optional[str] = None
    duration: Optional[float] = None
    timestamp: Optional[datetime] = None
    
    # Vulnerabilities
    vulnerabilities: List[Dict[str, Any]] = field(default_factory=list)
    
    # Raw output
    raw_output: Optional[str] = None
    raw_output_format: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> None:
        """Validate the result request data."""
        if not self.scan_id:
            raise ValueError("Scan ID cannot be empty")
        
        if not self.scanner:
            raise ValueError("Scanner name cannot be empty")
        
        if self.status not in ['SUCCESS', 'FAILED', 'PARTIAL']:
            raise ValueError("Status must be SUCCESS, FAILED, or PARTIAL")
        
        if self.duration is not None and self.duration < 0:
            raise ValueError("Duration cannot be negative")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for processing."""
        return {
            'scan_id': self.scan_id,
            'scanner': self.scanner,
            'status': self.status,
            'message': self.message,
            'duration': self.duration,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'vulnerabilities': self.vulnerabilities,
            'raw_output': self.raw_output,
            'raw_output_format': self.raw_output_format,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResultRequestDTO':
        """Create DTO from dictionary."""
        timestamp = None
        if data.get('timestamp'):
            timestamp = datetime.fromisoformat(data['timestamp'])
        
        return cls(
            scan_id=data['scan_id'],
            scanner=data['scanner'],
            status=data['status'],
            message=data.get('message'),
            duration=data.get('duration'),
            timestamp=timestamp,
            vulnerabilities=data.get('vulnerabilities', []),
            raw_output=data.get('raw_output'),
            raw_output_format=data.get('raw_output_format'),
            metadata=data.get('metadata', {}),
        )


@dataclass
class CancelScanRequestDTO:
    """Data Transfer Object for scan cancellation requests."""
    
    scan_id: str
    reason: Optional[str] = None
    force: bool = False
    cancelled_by: Optional[str] = None
    
    def validate(self) -> None:
        """Validate the cancellation request data."""
        if not self.scan_id:
            raise ValueError("Scan ID cannot be empty")
        
        if self.reason and len(self.reason) > 500:
            raise ValueError("Reason cannot exceed 500 characters")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for processing."""
        return {
            'scan_id': self.scan_id,
            'reason': self.reason,
            'force': self.force,
        }


@dataclass
class BatchScanRequestDTO:
    """Data Transfer Object for batch scan requests."""
    
    # Batch information
    name: str
    user_id: str
    
    # Optional batch information
    description: Optional[str] = None
    project_id: Optional[str] = None
    
    # Scan configuration (applied to all scans)
    config: Optional[Dict[str, Any]] = None
    scanners: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    # Individual scan targets
    targets: List[Dict[str, str]] = field(default_factory=list)  # [{"url": "...", "type": "..."}]
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> None:
        """Validate the batch scan request data."""
        if not self.name or not self.name.strip():
            raise ValueError("Batch scan name cannot be empty")
        
        if len(self.name) > 200:
            raise ValueError("Batch scan name cannot exceed 200 characters")
        
        if not self.targets:
            raise ValueError("At least one target must be specified")
        
        if not self.scanners:
            raise ValueError("At least one scanner must be specified")
        
        for target in self.targets:
            if not target.get('url') or not target['url'].strip():
                raise ValueError("Target URL cannot be empty")
            if not target.get('type'):
                raise ValueError("Target type must be specified")
        
        if self.description and len(self.description) > 1000:
            raise ValueError("Description cannot exceed 1000 characters")
        
        if self.tags and len(self.tags) > 10:
            raise ValueError("Cannot have more than 10 tags")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for processing."""
        return {
            'name': self.name,
            'description': self.description,
            'user_id': self.user_id,
            'project_id': self.project_id,
            'config': self.config,
            'scanners': self.scanners,
            'targets': self.targets,
            'tags': self.tags,
            'metadata': self.metadata,
        }