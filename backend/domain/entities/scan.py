"""
Scan Entity

This module defines the Scan entity which represents a security scan job.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import uuid4


class ScanStatus(str, Enum):
    """Scan status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"  # Worker lost / stale heartbeat (before re-queue)


class ScanType(str, Enum):
    """Scan type enumeration - matches scanner/core/scanner_registry.py ScanType."""
    CODE = "code"
    CONTAINER = "container"
    WEBSITE = "website"
    NETWORK = "network"
    MOBILE = "mobile"
    # Additional scanner scan types
    DEPENDENCY = "dependency"
    SECRETS = "secrets"
    CONFIG = "config"
    IMAGE = "image"


@dataclass
class Scan:
    """Security scan entity."""
    
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    scan_type: ScanType = ScanType.CODE
    status: ScanStatus = ScanStatus.PENDING
    target_url: str = ""
    target_type: str = ""
    scanners: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime = field(default_factory=datetime.utcnow)
    scheduled_at: Optional[datetime] = None  # Scheduled start time (optional)
    last_heartbeat_at: Optional[datetime] = None  # Worker/orchestrator liveness (running scans)

    # Results
    results: List[Dict[str, Any]] = field(default_factory=list)
    total_vulnerabilities: int = 0
    critical_vulnerabilities: int = 0
    high_vulnerabilities: int = 0
    medium_vulnerabilities: int = 0
    low_vulnerabilities: int = 0
    info_vulnerabilities: int = 0
    duration: Optional[int] = None  # Duration in seconds
    
    # Error handling
    error_message: Optional[str] = None
    retry_count: int = 0
    
    # Metadata
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    scan_metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata (e.g. session_id for guest sessions)
    
    # Queue priority (higher = earlier in queue)
    priority: int = 0
    
    def start(self):
        """Start the scan."""
        if self.status != ScanStatus.PENDING:
            raise ValueError("Scan can only be started from PENDING status")
        
        self.status = ScanStatus.RUNNING
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def complete(self, results: List[Dict[str, Any]], duration: int):
        """Complete the scan successfully."""
        if self.status != ScanStatus.RUNNING:
            raise ValueError("Scan can only be completed from RUNNING status")
        
        self.status = ScanStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.results = results
        self.duration = duration
        self.total_vulnerabilities = self._count_vulnerabilities(results)
    
    def fail(self, error_message: str):
        """Mark the scan as failed."""
        self.status = ScanStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.error_message = error_message
    
    def cancel(self):
        """Cancel the scan."""
        if self.status not in [ScanStatus.PENDING, ScanStatus.RUNNING]:
            raise ValueError("Scan can only be cancelled from PENDING or RUNNING status")
        
        self.status = ScanStatus.CANCELLED
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def retry(self):
        """Retry the scan."""
        if self.status not in (ScanStatus.FAILED, ScanStatus.INTERRUPTED):
            raise ValueError("Scan can only be retried from FAILED or INTERRUPTED status")
        
        self.status = ScanStatus.PENDING
        self.started_at = None
        self.completed_at = None
        self.error_message = None
        self.retry_count += 1
        self.updated_at = datetime.utcnow()
    
    def add_tag(self, tag: str):
        """Add a tag to the scan."""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.utcnow()
    
    def remove_tag(self, tag: str):
        """Remove a tag from the scan."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.utcnow()
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update scan configuration."""
        self.config.update(new_config)
        self.updated_at = datetime.utcnow()
    
    def get_duration(self) -> Optional[int]:
        """Get scan duration in seconds."""
        if self.duration is not None:
            return self.duration
        
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        
        if self.started_at and self.status == ScanStatus.RUNNING:
            return int((datetime.utcnow() - self.started_at).total_seconds())
        
        return None
    
    def is_completed(self) -> bool:
        """Check if scan is completed."""
        return self.status in [
            ScanStatus.COMPLETED,
            ScanStatus.FAILED,
            ScanStatus.CANCELLED,
            ScanStatus.INTERRUPTED,
        ]
    
    def is_successful(self) -> bool:
        """Check if scan completed successfully."""
        return self.status == ScanStatus.COMPLETED
    
    def has_vulnerabilities(self) -> bool:
        """Check if scan found vulnerabilities."""
        return self.total_vulnerabilities > 0
    
    def _count_vulnerabilities(self, results: List[Dict[str, Any]]) -> int:
        """Count vulnerabilities in scan results."""
        count = 0
        for result in results:
            if isinstance(result, dict) and 'vulnerabilities' in result:
                count += len(result['vulnerabilities'])
        return count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert scan to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'scan_type': self.scan_type.value,
            'status': self.status.value,
            'target_url': self.target_url,
            'target_type': self.target_type,
            'scanners': self.scanners,
            'config': self.config,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'updated_at': self.updated_at.isoformat(),
            'results': self.results,
            'total_vulnerabilities': self.total_vulnerabilities,
            'duration': self.get_duration(),
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'user_id': self.user_id,
            'project_id': self.project_id,
            'tags': self.tags,
            'scheduled_at': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'last_heartbeat_at': (
                self.last_heartbeat_at.isoformat() if self.last_heartbeat_at else None
            ),
            'scan_metadata': self.scan_metadata,
            'critical_vulnerabilities': self.critical_vulnerabilities,
            'high_vulnerabilities': self.high_vulnerabilities,
            'medium_vulnerabilities': self.medium_vulnerabilities,
            'low_vulnerabilities': self.low_vulnerabilities,
            'info_vulnerabilities': self.info_vulnerabilities,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Scan':
        """Create scan from dictionary."""
        scan = cls(
            id=data.get('id', str(uuid4())),
            name=data.get('name', ''),
            description=data.get('description', ''),
            scan_type=ScanType(data.get('scan_type', 'code')),
            status=ScanStatus(data.get('status', 'pending')),
            target_url=data.get('target_url', ''),
            target_type=data.get('target_type', ''),
            scanners=data.get('scanners', []),
            config=data.get('config', {}),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.utcnow().isoformat())),
            started_at=datetime.fromisoformat(data['started_at']) if data.get('started_at') else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            updated_at=datetime.fromisoformat(data.get('updated_at', datetime.utcnow().isoformat())),
            results=data.get('results', []),
            total_vulnerabilities=data.get('total_vulnerabilities', 0),
            duration=data.get('duration'),
            error_message=data.get('error_message'),
            retry_count=data.get('retry_count', 0),
            user_id=data.get('user_id'),
            project_id=data.get('project_id'),
            tags=data.get('tags', []),
            scheduled_at=datetime.fromisoformat(data['scheduled_at']) if data.get('scheduled_at') else None,
            last_heartbeat_at=(
                datetime.fromisoformat(data['last_heartbeat_at'])
                if data.get('last_heartbeat_at')
                else None
            ),
            scan_metadata=data.get('scan_metadata', {}),
            critical_vulnerabilities=data.get('critical_vulnerabilities', 0),
            high_vulnerabilities=data.get('high_vulnerabilities', 0),
            medium_vulnerabilities=data.get('medium_vulnerabilities', 0),
            low_vulnerabilities=data.get('low_vulnerabilities', 0),
            info_vulnerabilities=data.get('info_vulnerabilities', 0),
        )
        return scan