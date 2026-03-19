"""
Scanner Duration Service

Service for tracking and calculating scanner execution durations.
Uses ScannerDurationStatsRepository (DDD).
"""
import logging
from typing import List, Dict, Any, Optional

from domain.repositories.scanner_duration_stats_repository import ScannerDurationStatsRepository

logger = logging.getLogger(__name__)


def _get_repo() -> ScannerDurationStatsRepository:
    from infrastructure.container import get_scanner_duration_stats_repository
    return get_scanner_duration_stats_repository()


class ScannerDurationService:
    """Service for managing scanner duration statistics."""
    
    @staticmethod
    async def update_stats_from_scan_results(scan_results: List[Dict[str, Any]]) -> None:
        """Update duration statistics from scan results."""
        try:
            repo = _get_repo()
            for result in scan_results:
                scanner_name = result.get('scanner')
                duration = result.get('duration')
                if not scanner_name or not duration:
                    continue
                duration_seconds = int(duration) if isinstance(duration, (int, float)) else None
                if not duration_seconds or duration_seconds <= 0:
                    continue
                await repo.record_sample(scanner_name, duration_seconds)
            logger.debug("Updated scanner duration stats from %s results", len(scan_results))
        except Exception as e:
            logger.error("Failed to update scanner duration stats: %s", e, exc_info=True)
    
    @staticmethod
    async def get_estimated_time(scanners: List[str]) -> float:
        """Estimated time in seconds (sum of average durations)."""
        if not scanners:
            return 0.0
        try:
            repo = _get_repo()
            avgs = await repo.get_avgs_for_scanners(scanners)
            return float(sum(avgs.values()))
        except Exception as e:
            logger.error("Failed to get estimated time: %s", e, exc_info=True)
            return 0.0
    
    @staticmethod
    async def get_scanner_stats(scanner_name: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific scanner."""
        try:
            repo = _get_repo()
            all_list = await repo.get_all()
            for s in all_list:
                if s.get("scanner_name") == scanner_name:
                    return s
            return None
        except Exception as e:
            logger.error("Failed to get stats for scanner %s: %s", scanner_name, e, exc_info=True)
            return None
    
    @staticmethod
    async def get_all_stats() -> List[Dict[str, Any]]:
        """Get statistics for all scanners."""
        try:
            repo = _get_repo()
            return await repo.get_all()
        except Exception as e:
            logger.error("Failed to get all stats: %s", e, exc_info=True)
            return []
