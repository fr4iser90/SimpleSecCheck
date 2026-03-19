"""Blocked IP repository interface (DDD port)."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional

from domain.entities.blocked_ip import BlockedIP


class BlockedIPRepository(ABC):
    """Interface for blocked IP persistence."""

    @abstractmethod
    async def list_all(self, active_only: bool = True, limit: int = 500) -> List[BlockedIP]:
        """List blocked IPs. Order by blocked_at desc."""
        pass

    @abstractmethod
    async def get_by_ip(self, ip_address: str) -> Optional[BlockedIP]:
        """Get blocked IP by address."""
        pass

    @abstractmethod
    async def create(self, ip_address: str, reason: Optional[str] = None, blocked_by: Optional[str] = None, expires_at: Optional[datetime] = None) -> BlockedIP:
        """Create a new blocked IP. Raises if already exists."""
        pass

    @abstractmethod
    async def update(self, blocked_ip: BlockedIP) -> BlockedIP:
        """Update existing blocked IP (e.g. reactivate, change reason)."""
        pass

    @abstractmethod
    async def delete_by_ip(self, ip_address: str) -> bool:
        """Remove block for IP (set is_active=False). Returns True if found and deactivated."""
        pass

    @abstractmethod
    async def get_activity_stats(self, since: Optional[datetime] = None, ip_address: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get IP activity records (for admin). since = filter by created_at; ip_address = filter by IP. Order by count desc."""
        pass

    @abstractmethod
    async def get_stats(self, activity_since: Optional[datetime] = None) -> Dict[str, int]:
        """Get counts: total_blocked (active), total_activity_24h (IPActivity count since activity_since)."""
        pass
