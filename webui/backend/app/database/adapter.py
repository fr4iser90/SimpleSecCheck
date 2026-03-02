"""
Database Adapter Interface
Abstract base class for database operations
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime
import os


class DatabaseAdapter(ABC):
    """Abstract base class for database adapters"""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize database connection/setup"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close database connection"""
        pass
    
    # Session Management
    @abstractmethod
    async def create_session(self, session_id: str, ip_address: Optional[str] = None) -> Dict[str, Any]:
        """Create a new session"""
        pass
    
    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        pass
    
    @abstractmethod
    async def update_session(self, session_id: str, **kwargs) -> bool:
        """Update session data"""
        pass
    
    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        pass
    
    @abstractmethod
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions, returns count of deleted sessions"""
        pass
    
    # Queue Management
    @abstractmethod
    async def add_to_queue(
        self,
        session_id: str,
        repository_url: str,
        repository_name: str,
        branch: Optional[str] = None,
        commit_hash: Optional[str] = None,
    ) -> str:
        """Add scan to queue, returns queue_id"""
        pass
    
    @abstractmethod
    async def get_queue_item(self, queue_id: str) -> Optional[Dict[str, Any]]:
        """Get queue item by ID"""
        pass
    
    @abstractmethod
    async def get_queue(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get queue items (public, anonymized)"""
        pass
    
    @abstractmethod
    async def get_queue_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Get queue items for a specific session"""
        pass
    
    @abstractmethod
    async def update_queue_status(
        self,
        queue_id: str,
        status: str,
        scan_id: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ) -> bool:
        """Update queue item status"""
        pass
    
    @abstractmethod
    async def get_next_queue_item(self) -> Optional[Dict[str, Any]]:
        """Get next pending queue item (FIFO)"""
        pass
    
    @abstractmethod
    async def get_queue_length(self) -> int:
        """Get current queue length"""
        pass
    
    @abstractmethod
    async def find_duplicate_in_queue(
        self,
        repository_url: str,
        branch: Optional[str] = None,
        commit_hash: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Find duplicate scan in queue"""
        pass
    
    # Metadata Management
    @abstractmethod
    async def save_scan_metadata(
        self,
        repository_url: str,
        branch: str,
        commit_hash: str,
        scan_id: str,
        findings_count: int,
        metadata_file_path: Optional[str] = None,
    ) -> bool:
        """Save scan metadata for deduplication"""
        pass
    
    @abstractmethod
    async def find_duplicate_scan(
        self,
        repository_url: str,
        branch: str,
        commit_hash: str,
        max_age_days: int = 7,
    ) -> Optional[Dict[str, Any]]:
        """Find duplicate scan by metadata"""
        pass
    
    # Statistics
    @abstractmethod
    async def increment_statistics(
        self,
        findings_by_severity: Dict[str, int],
        findings_by_tool: Dict[str, int],
        false_positive_count: int = 0,
    ) -> bool:
        """Increment statistics counters"""
        pass
    
    @abstractmethod
    async def get_statistics(self) -> Dict[str, Any]:
        """Get aggregated statistics"""
        pass


def get_database() -> DatabaseAdapter:
    """
    Factory function to get appropriate database adapter based on environment
    """
    database_type = os.getenv("DATABASE_TYPE", "file").lower()
    
    if database_type == "postgresql":
        from .postgresql_database import PostgreSQLDatabase
        return PostgreSQLDatabase()
    else:
        from .file_database import FileDatabase
        return FileDatabase()
