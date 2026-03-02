"""
Queue Service
Manages scan queue with deduplication and FIFO processing
"""

import os
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.database import get_database


class QueueService:
    """Service for managing scan queue"""
    
    def __init__(self):
        self.db = get_database()
        self.max_queue_length = int(os.getenv("MAX_QUEUE_LENGTH", "1000"))
        self.deduplication_enabled = os.getenv("QUEUE_DEDUPLICATION", "true").lower() == "true"
    
    async def initialize(self):
        """Initialize database connection"""
        await self.db.initialize()
    
    async def close(self):
        """Close database connection"""
        await self.db.close()
    
    def anonymize_repository_url(self, url: str) -> str:
        """Anonymize repository URL using SHA256 hash"""
        normalized = self._normalize_url(url)
        hash_obj = hashlib.sha256(normalized.encode())
        hash_hex = hash_obj.hexdigest()
        short_hash = hash_hex[:8]
        return f"repo_{short_hash}"
    
    def _normalize_url(self, url: str) -> str:
        """Normalize repository URL"""
        url = url.rstrip(".git").rstrip("/")
        if url.startswith("git@"):
            url = url.replace("git@", "https://").replace(":", "/")
        return url
    
    async def add_scan_to_queue(
        self,
        session_id: str,
        repository_url: str,
        branch: Optional[str] = None,
        commit_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Add scan to queue with deduplication
        Returns queue item or duplicate info
        """
        # Check queue length
        queue_length = await self.db.get_queue_length()
        if queue_length >= self.max_queue_length:
            return {
                "error": "queue_full",
                "message": f"Queue is full (max {self.max_queue_length} items). Please try again later.",
                "queue_length": queue_length,
            }
        
        # Check for duplicates if deduplication is enabled
        if self.deduplication_enabled:
            duplicate = await self.db.find_duplicate_in_queue(
                repository_url, branch, commit_hash
            )
            
            if duplicate:
                # Return existing queue item
                return {
                    "queue_id": duplicate["queue_id"],
                    "status": duplicate["status"],
                    "message": "Identical scan already in queue. You will receive the same results.",
                    "duplicate_of": duplicate["queue_id"],
                    "position": duplicate.get("position"),
                }
        
        # Anonymize repository name
        repository_name = self.anonymize_repository_url(repository_url)
        
        # Add to queue
        queue_id = await self.db.add_to_queue(
            session_id=session_id,
            repository_url=self._normalize_url(repository_url),
            repository_name=repository_name,
            branch=branch,
            commit_hash=commit_hash,
        )
        
        # Get queue item
        queue_item = await self.db.get_queue_item(queue_id)
        
        return {
            "queue_id": queue_id,
            "status": "pending",
            "position": queue_item.get("position") if queue_item else None,
            "message": "Scan added to queue",
        }
    
    async def get_queue_status(self, queue_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a queue item"""
        return await self.db.get_queue_item(queue_id)
    
    async def get_public_queue(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get public queue (anonymized)"""
        return await self.db.get_queue(limit=limit)
    
    async def get_user_queue(self, session_id: str) -> List[Dict[str, Any]]:
        """Get queue items for a specific session"""
        return await self.db.get_queue_by_session(session_id)
    
    async def get_next_job(self) -> Optional[Dict[str, Any]]:
        """Get next job from queue (for scanner worker)"""
        return await self.db.get_next_queue_item()
    
    async def update_job_status(
        self,
        queue_id: str,
        status: str,
        scan_id: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ) -> bool:
        """Update job status in queue"""
        return await self.db.update_queue_status(
            queue_id=queue_id,
            status=status,
            scan_id=scan_id,
            started_at=started_at,
            completed_at=completed_at,
        )
    
    async def get_queue_length(self) -> int:
        """Get current queue length"""
        return await self.db.get_queue_length()


# Global queue service instance
_queue_service: Optional[QueueService] = None


async def get_queue_service() -> QueueService:
    """Get or create queue service instance"""
    global _queue_service
    if _queue_service is None:
        _queue_service = QueueService()
        await _queue_service.initialize()
    return _queue_service
