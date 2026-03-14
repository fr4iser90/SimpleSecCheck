"""
Scan Repository Interface

This module defines the ScanRepository interface for accessing scan data.
This is a domain layer interface that should be implemented by infrastructure layer.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID

from domain.entities.scan import Scan, ScanStatus, ScanType


class ScanRepository(ABC):
    """Interface for scan repository operations."""
    
    @abstractmethod
    async def create(self, scan: Scan) -> Scan:
        """Create a new scan."""
        pass
    
    @abstractmethod
    async def get_by_id(self, scan_id: str) -> Optional[Scan]:
        """Get scan by ID."""
        pass
    
    @abstractmethod
    async def get_by_user(self, user_id: str, limit: int = 100, offset: int = 0) -> List[Scan]:
        """Get scans by user."""
        pass
    
    @abstractmethod
    async def get_by_project(self, project_id: str, limit: int = 100, offset: int = 0) -> List[Scan]:
        """Get scans by project."""
        pass
    
    @abstractmethod
    async def get_by_status(self, status: ScanStatus, limit: int = 100, offset: int = 0) -> List[Scan]:
        """Get scans by status."""
        pass
    
    @abstractmethod
    async def get_by_type(self, scan_type: ScanType, limit: int = 100, offset: int = 0) -> List[Scan]:
        """Get scans by type."""
        pass
    
    @abstractmethod
    async def update(self, scan: Scan) -> Scan:
        """Update scan."""
        pass
    
    @abstractmethod
    async def delete(self, scan_id: str) -> bool:
        """Delete scan."""
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def count_scans(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        status: Optional[ScanStatus] = None,
        scan_type: Optional[ScanType] = None,
        tags: Optional[List[str]] = None
    ) -> int:
        """Count scans with optional filtering."""
        pass
    
    @abstractmethod
    async def add_tag(self, scan_id: str, tag: str) -> bool:
        """Add tag to scan."""
        pass
    
    @abstractmethod
    async def remove_tag(self, scan_id: str, tag: str) -> bool:
        """Remove tag from scan."""
        pass
    
    @abstractmethod
    async def update_status(self, scan_id: str, status: ScanStatus) -> bool:
        """Update scan status."""
        pass
    
    @abstractmethod
    async def update_results(self, scan_id: str, results: List[Dict[str, Any]]) -> bool:
        """Update scan results."""
        pass
    
    @abstractmethod
    async def get_recent_scans(self, limit: int = 10) -> List[Scan]:
        """Get recent scans."""
        pass
    
    @abstractmethod
    async def get_scan_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get scan statistics."""
        pass