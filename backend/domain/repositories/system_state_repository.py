"""System state repository interface (DDD port)."""
from abc import ABC, abstractmethod
from typing import Optional

from domain.entities.system_state import SystemState


class SystemStateRepository(ABC):
    """Interface for system state singleton persistence."""

    @abstractmethod
    async def get_singleton(self) -> Optional[SystemState]:
        """Get the single system state row, or None if not found."""
        pass

    @abstractmethod
    async def save(self, state: SystemState) -> SystemState:
        """Create or update the system state."""
        pass

    @abstractmethod
    async def table_exists(self) -> bool:
        """Return True if system_state table exists (for bootstrap)."""
        pass
