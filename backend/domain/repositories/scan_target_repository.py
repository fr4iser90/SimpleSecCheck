"""
ScanTarget Repository Interface

Single source of truth for user-saved targets (My Targets).
"""
from abc import ABC, abstractmethod
from typing import List, Optional

from domain.entities.scan_target import ScanTarget


class ScanTargetRepository(ABC):
    """Interface for scan target persistence."""

    @abstractmethod
    async def create(self, target: ScanTarget) -> ScanTarget:
        """Persist a new target. Raises if user_id+source duplicate."""
        pass

    @abstractmethod
    async def get_by_id(self, target_id: str, user_id: str) -> Optional[ScanTarget]:
        """Get target by id; must belong to user."""
        pass

    @abstractmethod
    async def list_by_user(
        self,
        user_id: str,
        target_type: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> List[ScanTarget]:
        """List targets for user, optionally filtered by type."""
        pass

    @abstractmethod
    async def update(self, target: ScanTarget) -> ScanTarget:
        """Update existing target. Target must belong to user."""
        pass

    @abstractmethod
    async def delete(self, target_id: str, user_id: str) -> bool:
        """Delete target. Returns True if deleted."""
        pass

    @abstractmethod
    async def exists_for_user(self, user_id: str, source: str, target_type: str) -> bool:
        """True if user already has a target with this source and type (for uniqueness)."""
        pass
