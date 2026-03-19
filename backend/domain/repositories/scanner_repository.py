"""Scanner repository interface (DDD port)."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from domain.entities.scanner import Scanner


class ScannerRepository(ABC):
    """Interface for scanner persistence (discovery cache)."""

    @abstractmethod
    async def list_all(self) -> List[Scanner]:
        """List all scanners, ordered by name."""
        pass

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Scanner]:
        """Get scanner by name."""
        pass

    @abstractmethod
    async def get_by_tools_key(self, tools_key: str) -> Optional[Scanner]:
        """Get scanner by metadata tools_key (slug, e.g. semgrep, sonarqube)."""
        pass

    @abstractmethod
    async def create_or_update_from_dict(self, data: Dict[str, Any]) -> Scanner:
        """Create or update a scanner from dict (name, scan_types, priority, enabled, ...). Returns entity."""
        pass

    @abstractmethod
    async def sync_all(self, scanners_data: List[Dict[str, Any]]) -> None:
        """Create or update all scanners from a list of dicts (e.g. from worker API)."""
        pass

    @abstractmethod
    async def table_exists(self) -> bool:
        """Return True if scanners table exists."""
        pass
