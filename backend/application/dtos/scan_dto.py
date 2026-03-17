"""
Scan DTO (Data Transfer Object)

This module defines DTOs for scan-related data transfer between layers.
DTOs are used to transfer data without exposing domain entities directly.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from uuid import UUID

from domain.entities.scan import ScanStatus, ScanType
from domain.value_objects.scan_config import ScanConfig
from domain.value_objects.vulnerability_severity import VulnerabilitySeverity


@dataclass
class ScanDTO:
    """Data Transfer Object for Scan entities."""
    
    # Basic scan information
    id: str
    name: str
    description: str
    scan_type: ScanType
    target_url: str
    target_type: str
    
    # User and project information
    user_id: str
    project_id: Optional[str] = None
    
    # Scan configuration
    config: Optional[ScanConfig] = None
    scanners: List[str] = field(default_factory=list)
    
    # Status and timing
    status: ScanStatus = ScanStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None
    
    # Results and statistics
    tags: List[str] = field(default_factory=list)
    results: List[Dict[str, Any]] = field(default_factory=list)
    total_vulnerabilities: int = 0
    critical_vulnerabilities: int = 0
    high_vulnerabilities: int = 0
    medium_vulnerabilities: int = 0
    low_vulnerabilities: int = 0
    info_vulnerabilities: int = 0
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_entity(cls, scan: 'Scan') -> 'ScanDTO':
        """Create DTO from Scan entity."""
        return cls(
            id=str(scan.id),
            name=scan.name,
            description=scan.description,
            scan_type=scan.scan_type,
            target_url=scan.target_url,
            target_type=scan.target_type,
            user_id=scan.user_id,
            project_id=scan.project_id,
            config=scan.config,
            scanners=scan.scanners,
            status=scan.status,
            created_at=scan.created_at,
            started_at=scan.started_at,
            completed_at=scan.completed_at,
            scheduled_at=scan.scheduled_at,
            tags=scan.tags,
            results=scan.results,
            total_vulnerabilities=scan.total_vulnerabilities,
            critical_vulnerabilities=scan.critical_vulnerabilities,
            high_vulnerabilities=scan.high_vulnerabilities,
            medium_vulnerabilities=scan.medium_vulnerabilities,
            low_vulnerabilities=scan.low_vulnerabilities,
            info_vulnerabilities=scan.info_vulnerabilities,
            metadata=scan.scan_metadata,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'scan_type': self.scan_type.value,
            'target_url': self.target_url,
            'target_type': self.target_type,
            'user_id': self.user_id,
            'project_id': self.project_id,
            'config': self.config.to_dict() if self.config else None,
            'scanners': self.scanners,
            'status': self.status.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'scheduled_at': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'tags': self.tags,
            'results': self.results,
            'total_vulnerabilities': self.total_vulnerabilities,
            'critical_vulnerabilities': self.critical_vulnerabilities,
            'high_vulnerabilities': self.high_vulnerabilities,
            'medium_vulnerabilities': self.medium_vulnerabilities,
            'low_vulnerabilities': self.low_vulnerabilities,
            'info_vulnerabilities': self.info_vulnerabilities,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScanDTO':
        """Create DTO from dictionary."""
        config_data = data.get('config')
        config = ScanConfig.from_dict(config_data) if config_data else None
        
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            scan_type=ScanType(data['scan_type']),
            target_url=data['target_url'],
            target_type=data['target_type'],
            user_id=data['user_id'],
            project_id=data.get('project_id'),
            config=config,
            scanners=data.get('scanners', []),
            status=ScanStatus(data['status']),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            started_at=datetime.fromisoformat(data['started_at']) if data.get('started_at') else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            scheduled_at=datetime.fromisoformat(data['scheduled_at']) if data.get('scheduled_at') else None,
            tags=data.get('tags', []),
            results=data.get('results', []),
            total_vulnerabilities=data.get('total_vulnerabilities', 0),
            critical_vulnerabilities=data.get('critical_vulnerabilities', 0),
            high_vulnerabilities=data.get('high_vulnerabilities', 0),
            medium_vulnerabilities=data.get('medium_vulnerabilities', 0),
            low_vulnerabilities=data.get('low_vulnerabilities', 0),
            info_vulnerabilities=data.get('info_vulnerabilities', 0),
            metadata=data.get('metadata', {}),
        )


@dataclass
class ScanSummaryDTO:
    """Summary DTO for listing scans."""
    
    id: str
    name: str
    scan_type: ScanType
    target_url: str
    target_type: str
    status: ScanStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_vulnerabilities: int = 0
    critical_vulnerabilities: int = 0
    high_vulnerabilities: int = 0
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    @classmethod
    def from_entity(cls, scan: 'Scan') -> 'ScanSummaryDTO':
        """Create summary DTO from Scan entity."""
        return cls(
            id=str(scan.id),
            name=scan.name,
            scan_type=scan.scan_type,
            target_url=scan.target_url,
            target_type=scan.target_type,
            status=scan.status,
            created_at=scan.created_at,
            started_at=scan.started_at,
            completed_at=scan.completed_at,
            total_vulnerabilities=scan.total_vulnerabilities,
            critical_vulnerabilities=scan.critical_vulnerabilities,
            high_vulnerabilities=scan.high_vulnerabilities,
            user_id=scan.user_id,
            project_id=scan.project_id,
            tags=scan.tags,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'scan_type': self.scan_type.value,
            'target_url': self.target_url,
            'target_type': self.target_type,
            'status': self.status.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'total_vulnerabilities': self.total_vulnerabilities,
            'critical_vulnerabilities': self.critical_vulnerabilities,
            'high_vulnerabilities': self.high_vulnerabilities,
            'user_id': self.user_id,
            'project_id': self.project_id,
            'tags': self.tags,
        }


@dataclass
class ScanStatisticsDTO:
    """DTO for scan statistics."""
    
    total_scans: int = 0
    pending_scans: int = 0
    running_scans: int = 0
    completed_scans: int = 0
    failed_scans: int = 0
    cancelled_scans: int = 0
    
    # Vulnerability statistics
    total_vulnerabilities: int = 0
    critical_vulnerabilities: int = 0
    high_vulnerabilities: int = 0
    medium_vulnerabilities: int = 0
    low_vulnerabilities: int = 0
    info_vulnerabilities: int = 0
    
    # Scan type statistics
    repository_scans: int = 0
    container_scans: int = 0
    infrastructure_scans: int = 0
    web_application_scans: int = 0
    
    # Time statistics
    average_scan_duration: float = 0.0  # in seconds
    longest_scan_duration: float = 0.0
    shortest_scan_duration: float = 0.0
    # Per-tool duration stats (from ScannerDurationStats)
    scanner_duration_stats: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'total_scans': self.total_scans,
            'pending_scans': self.pending_scans,
            'running_scans': self.running_scans,
            'completed_scans': self.completed_scans,
            'failed_scans': self.failed_scans,
            'cancelled_scans': self.cancelled_scans,
            'total_vulnerabilities': self.total_vulnerabilities,
            'critical_vulnerabilities': self.critical_vulnerabilities,
            'high_vulnerabilities': self.high_vulnerabilities,
            'medium_vulnerabilities': self.medium_vulnerabilities,
            'low_vulnerabilities': self.low_vulnerabilities,
            'info_vulnerabilities': self.info_vulnerabilities,
            'repository_scans': self.repository_scans,
            'container_scans': self.container_scans,
            'infrastructure_scans': self.infrastructure_scans,
            'web_application_scans': self.web_application_scans,
            'average_scan_duration': self.average_scan_duration,
            'longest_scan_duration': self.longest_scan_duration,
            'shortest_scan_duration': self.shortest_scan_duration,
            'scanner_duration_stats': self.scanner_duration_stats,
        }