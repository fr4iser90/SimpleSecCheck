"""Scanner tool settings repository interface (DDD port)."""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

from domain.entities.scanner_tool_settings import ScannerToolSettings


class ScannerToolSettingsRepository(ABC):
    """Interface for scanner_tool_settings persistence."""

    @abstractmethod
    async def list_all(self) -> List[ScannerToolSettings]:
        """List all scanner tool settings."""
        pass

    @abstractmethod
    async def get_by_key(self, scanner_key: str) -> Optional[ScannerToolSettings]:
        """Get settings by tools_key."""
        pass

    @abstractmethod
    async def save(self, settings: ScannerToolSettings) -> ScannerToolSettings:
        """Insert or update (upsert) by scanner_key."""
        pass

    @abstractmethod
    async def delete_by_key(self, scanner_key: str) -> bool:
        """Delete override for scanner_key. Returns True if deleted."""
        pass
