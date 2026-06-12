"""
Scanner Duration Service

Service for tracking and calculating scanner execution durations.
Uses ScannerDurationStatsRepository (DDD).
"""
import logging
from typing import List, Dict, Any, Optional

from domain.repositories.scanner_duration_stats_repository import ScannerDurationStatsRepository
from shared.scanner_duration_stats import MAX_SAMPLES

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
    async def get_estimated_time(scanners: List[str]) -> Optional[float]:
        """Estimated time in seconds when every scanner has measured data; else None."""
        if not scanners:
            return None
        try:
            repo = _get_repo()
            total = await repo.estimate_total_seconds(scanners)
            return float(total) if total is not None else None
        except Exception as e:
            logger.error("Failed to get estimated time: %s", e, exc_info=True)
            return None

    @staticmethod
    async def get_estimate_breakdown(scanners: List[str]) -> Dict[str, Any]:
        """Per-scanner measured estimates; total only when all selected scanners have data."""
        cleaned = [s.strip() for s in (scanners or []) if s and str(s).strip()]
        if not cleaned:
            return {
                "estimated_time_seconds": None,
                "max_samples": MAX_SAMPLES,
                "scanners": [],
            }
        try:
            repo = _get_repo()
            avgs = await repo.get_avgs_for_scanners(cleaned)
            all_stats = await repo.get_all()
            counts = {s["scanner_name"]: s.get("sample_count", 0) for s in all_stats}
            total = await repo.estimate_total_seconds(cleaned)
        except Exception as e:
            logger.error("Failed to get estimate breakdown: %s", e, exc_info=True)
            avgs = {}
            counts = {}
            total = None

        items = []
        for name in cleaned:
            measured = avgs.get(name)
            if measured is None:
                continue
            items.append({
                "scanner_name": name,
                "duration_seconds": measured,
                "sample_count": counts.get(name),
            })

        return {
            "estimated_time_seconds": total,
            "max_samples": MAX_SAMPLES,
            "scanners": items,
        }
    
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
