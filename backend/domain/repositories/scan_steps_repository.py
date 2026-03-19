"""Scan steps read repository (DDD port)."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ScanStepsRepository(ABC):
    """Interface for reading scan steps (DB-backed step UI)."""

    @abstractmethod
    async def get_steps_for_scan(self, scan_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Load step rows for a scan from scan_steps table.
        Returns None on error or when table not available; returns list of step dicts otherwise.
        Each dict has keys: number, name, status, message, started_at, completed_at, substeps, timeout_seconds.
        """
        pass
