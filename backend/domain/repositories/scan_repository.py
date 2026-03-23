"""
Scan Repository Interface

This module defines the ScanRepository interface for accessing scan data.
This is a domain layer interface that should be implemented by infrastructure layer.
"""
from abc import ABC, abstractmethod
from datetime import datetime
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
        guest_session_id: Optional[str] = None,
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
        guest_session_id: Optional[str] = None,
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
    async def get_recent_scans(
        self,
        limit: int = 10,
        *,
        owner_user_id: Optional[str] = None,
        guest_session_id: Optional[str] = None,
    ) -> List[Scan]:
        """Recent scans for an owner (user_id or guest session). Empty if neither set."""
        pass
    
    @abstractmethod
    async def get_scan_statistics(
        self,
        user_id: Optional[str] = None,
        guest_session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get scan statistics."""
        pass

    @abstractmethod
    async def count_scans_created_since(
        self,
        since: datetime,
        *,
        global_all: bool = False,
        user_id: Optional[str] = None,
        guest_session_id: Optional[str] = None,
    ) -> int:
        """Count scans with created_at >= since. Use exactly one of global_all, user_id, or guest_session_id."""

    @abstractmethod
    async def count_active_scans_for_actor(
        self,
        *,
        user_id: Optional[str] = None,
        guest_session_id: Optional[str] = None,
    ) -> int:
        """Count scans in pending or running for the given user or guest session."""

    @abstractmethod
    async def find_active_scan_by_user_and_target(
        self, user_id: str, target_url_contains: str
    ) -> Optional[Scan]:
        """Find one active (pending/running) scan for user where target_url contains the given substring."""
        pass

    @abstractmethod
    async def find_latest_finished_scan_by_user_and_target(
        self, user_id: str, target_url: str
    ) -> Optional[Scan]:
        """Latest scan for user+target_url with status in completed/failed/cancelled/interrupted (for interval scheduling)."""
        pass

    @abstractmethod
    async def get_queue_position(self, scan_id: str, user_id: str) -> Optional[int]:
        """Get 1-based queue position among user's pending scans. None if not pending."""
        pass

    @abstractmethod
    async def get_queue_items(
        self,
        status_filter: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Scan]:
        """Get scans for queue view: by status (default pending+running), ordered by priority desc, created_at asc."""
        pass

    @abstractmethod
    async def count_by_statuses(self, statuses: List[str]) -> int:
        """Count scans with status in statuses."""
        pass

    @abstractmethod
    async def get_latest_scans_by_target_urls(
        self, user_id: str, target_urls: List[str]
    ) -> Dict[str, Scan]:
        """Latest scan per target_url for user. Keys are target_url."""
        pass

    @abstractmethod
    async def get_active_scans_by_target_urls(
        self, user_id: str, target_urls: List[str]
    ) -> Dict[str, Scan]:
        """Newest pending/running scan per target_url for user. Keys match stored target_url."""
        pass

    @abstractmethod
    async def get_position_in_queue(self, scan_id: str) -> Optional[int]:
        """1-based position of scan among all pending+running (by priority desc, created_at asc). None if not found or not pending/running."""
        pass

    @abstractmethod
    async def list_scans_for_actor(
        self,
        user_id: Optional[str] = None,
        guest_session_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 100,
    ) -> List[Scan]:
        """List scans for user or guest, ordered by priority desc, created_at desc (for my-scans view)."""
        pass

    @abstractmethod
    async def get_scans_before_in_queue(self, scan_id: str) -> List[Scan]:
        """Scans that are before this one in the queue (pending+running). For estimated wait time."""
        pass

    @abstractmethod
    async def get_running_scans(self, limit: int = 50) -> List[Scan]:
        """Running scans ordered by started_at asc (for admin queue overview)."""
        pass

    @abstractmethod
    async def count_today_by_filters(
        self,
        status: Optional[str] = None,
        error_message_contains: Optional[str] = None,
    ) -> int:
        """Count scans created today matching status and/or error_message fragment."""
        pass

    @abstractmethod
    async def get_avg_duration_completed_today(self) -> Optional[float]:
        """Average duration in seconds for scans completed today (with non-null duration)."""
        pass

    @abstractmethod
    async def get_stale_running_scan_ids(
        self,
        stale_cutoff: "datetime",
        null_cutoff: "datetime",
        limit: int = 200,
    ) -> List[str]:
        """Ids of running scans with stale or missing heartbeat (for recovery)."""
        pass