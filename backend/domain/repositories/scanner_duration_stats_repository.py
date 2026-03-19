"""Scanner duration stats repository interface (DDD port)."""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class ScannerDurationStatsRepository(ABC):
    """Interface for scanner_duration_stats persistence."""

    @abstractmethod
    async def record_sample(self, scanner_name: str, duration_seconds: int) -> None:
        """Record a duration sample (rolling average, max 100 samples)."""
        pass

    @abstractmethod
    async def get_avg_by_scanner(self, scanner_name: str) -> Optional[int]:
        """Get average duration in seconds for one scanner. None if no data."""
        pass

    @abstractmethod
    async def get_avgs_for_scanners(self, scanner_names: List[str]) -> Dict[str, int]:
        """Get average duration per scanner. Only includes scanners with data."""
        pass

    @abstractmethod
    async def get_all(self) -> List[Dict]:
        """Get all stats (for admin). List of dicts with scanner_name, avg, min, max, sample_count, last_updated."""
        pass
