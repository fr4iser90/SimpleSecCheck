"""
Scanner Duration Service

Service for tracking and calculating scanner execution durations.
Used to estimate scan completion times based on historical data.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import select, func

from infrastructure.database.adapter import db_adapter
from infrastructure.database.models import ScannerDurationStats

logger = logging.getLogger(__name__)

# Maximum number of samples to keep for rolling average
MAX_SAMPLES = 100
# Default duration if no stats available (2 minutes)
DEFAULT_DURATION_SECONDS = 120


class ScannerDurationService:
    """Service for managing scanner duration statistics."""
    
    @staticmethod
    async def update_stats_from_scan_results(scan_results: List[Dict[str, Any]]) -> None:
        """
        Update duration statistics from scan results.
        
        Args:
            scan_results: List of scan result dictionaries, each containing:
                - scanner: str (scanner name)
                - duration: float (duration in seconds)
        """
        try:
            await db_adapter.ensure_initialized()
            
            async with db_adapter.async_session() as session:
                for result in scan_results:
                    scanner_name = result.get('scanner')
                    duration = result.get('duration')
                    
                    if not scanner_name or not duration:
                        continue
                    
                    # Convert duration to integer (seconds)
                    duration_seconds = int(duration) if isinstance(duration, (int, float)) else None
                    if not duration_seconds or duration_seconds <= 0:
                        continue
                    
                    await ScannerDurationService._update_scanner_stat(
                        session, scanner_name, duration_seconds
                    )
                
                await session.commit()
                logger.debug(f"Updated scanner duration stats from {len(scan_results)} results")
                
        except Exception as e:
            logger.error(f"Failed to update scanner duration stats: {e}", exc_info=True)
    
    @staticmethod
    async def _update_scanner_stat(session, scanner_name: str, duration_seconds: int) -> None:
        """Update statistics for a single scanner."""
        try:
            # Get existing stats
            result = await session.execute(
                select(ScannerDurationStats).where(
                    ScannerDurationStats.scanner_name == scanner_name
                )
            )
            stats = result.scalar_one_or_none()
            
            if stats:
                # Update existing stats with rolling average
                # Calculate new average: (old_avg * old_count + new_duration) / (old_count + 1)
                # But cap at MAX_SAMPLES to keep rolling average
                old_count = min(stats.sample_count, MAX_SAMPLES - 1)
                old_avg = stats.avg_duration_seconds
                
                # Rolling average calculation
                new_count = old_count + 1
                new_avg = int((old_avg * old_count + duration_seconds) / new_count)
                
                stats.avg_duration_seconds = new_avg
                stats.sample_count = stats.sample_count + 1
                
                # Update min/max
                if stats.min_duration_seconds is None or duration_seconds < stats.min_duration_seconds:
                    stats.min_duration_seconds = duration_seconds
                if stats.max_duration_seconds is None or duration_seconds > stats.max_duration_seconds:
                    stats.max_duration_seconds = duration_seconds
                
                stats.last_updated = datetime.utcnow()
            else:
                # Create new stats entry
                stats = ScannerDurationStats(
                    scanner_name=scanner_name,
                    avg_duration_seconds=duration_seconds,
                    min_duration_seconds=duration_seconds,
                    max_duration_seconds=duration_seconds,
                    sample_count=1,
                    last_updated=datetime.utcnow()
                )
                session.add(stats)
            
        except Exception as e:
            logger.error(f"Failed to update stat for scanner {scanner_name}: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def get_estimated_time(scanners: List[str]) -> float:
        """
        Get estimated time for a list of scanners.
        
        Args:
            scanners: List of scanner names
            
        Returns:
            Estimated time in seconds (sum of average durations)
        """
        if not scanners:
            return 0.0
        
        try:
            await db_adapter.ensure_initialized()
            
            async with db_adapter.async_session() as session:
                total_seconds = 0.0
                
                for scanner_name in scanners:
                    result = await session.execute(
                        select(ScannerDurationStats).where(
                            ScannerDurationStats.scanner_name == scanner_name
                        )
                    )
                    stats = result.scalar_one_or_none()
                    
                    if stats and stats.sample_count > 0:
                        total_seconds += stats.avg_duration_seconds
                    else:
                        # Use default if no stats available
                        total_seconds += DEFAULT_DURATION_SECONDS
                
                return total_seconds
                
        except Exception as e:
            logger.error(f"Failed to get estimated time: {e}", exc_info=True)
            # Fallback: return default * number of scanners
            return len(scanners) * DEFAULT_DURATION_SECONDS
    
    @staticmethod
    async def get_scanner_stats(scanner_name: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a specific scanner.
        
        Args:
            scanner_name: Name of the scanner
            
        Returns:
            Dictionary with stats or None if not found
        """
        try:
            await db_adapter.ensure_initialized()
            
            async with db_adapter.async_session() as session:
                result = await session.execute(
                    select(ScannerDurationStats).where(
                        ScannerDurationStats.scanner_name == scanner_name
                    )
                )
                stats = result.scalar_one_or_none()
                
                if not stats:
                    return None
                
                return {
                    'scanner_name': stats.scanner_name,
                    'avg_duration_seconds': stats.avg_duration_seconds,
                    'min_duration_seconds': stats.min_duration_seconds,
                    'max_duration_seconds': stats.max_duration_seconds,
                    'sample_count': stats.sample_count,
                    'last_updated': stats.last_updated.isoformat() if stats.last_updated else None
                }
                
        except Exception as e:
            logger.error(f"Failed to get stats for scanner {scanner_name}: {e}", exc_info=True)
            return None
    
    @staticmethod
    async def get_all_stats() -> List[Dict[str, Any]]:
        """
        Get statistics for all scanners.
        
        Returns:
            List of stat dictionaries
        """
        try:
            await db_adapter.ensure_initialized()
            
            async with db_adapter.async_session() as session:
                result = await session.execute(select(ScannerDurationStats))
                all_stats = result.scalars().all()
                
                return [
                    {
                        'scanner_name': stats.scanner_name,
                        'avg_duration_seconds': stats.avg_duration_seconds,
                        'min_duration_seconds': stats.min_duration_seconds,
                        'max_duration_seconds': stats.max_duration_seconds,
                        'sample_count': stats.sample_count,
                        'last_updated': stats.last_updated.isoformat() if stats.last_updated else None
                    }
                    for stats in all_stats
                ]
                
        except Exception as e:
            logger.error(f"Failed to get all stats: {e}", exc_info=True)
            return []
