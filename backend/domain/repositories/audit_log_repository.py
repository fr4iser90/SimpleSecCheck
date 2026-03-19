"""Audit log repository interface (DDD port)."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from domain.entities.audit_log_entry import AuditLogEntry


class AuditLogRepository(ABC):
    """Interface for audit log persistence."""

    @abstractmethod
    async def add(
        self,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        action_type: str = "",
        target: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        result: str = "success",
    ) -> None:
        """Append one audit log entry."""
        pass

    @abstractmethod
    async def get_entries(
        self,
        limit: int = 100,
        offset: int = 0,
        user_id: Optional[str] = None,
        action_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get entries with filters and pagination. Returns (entries_list, total_count)."""
        pass
