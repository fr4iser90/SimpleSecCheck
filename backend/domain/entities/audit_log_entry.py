"""Audit log entry entity."""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class AuditLogEntry:
    """Single audit log record."""
    id: str
    user_id: Optional[str]
    user_email: Optional[str]
    action_type: str
    target: Optional[str]
    details: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]
    result: str
    created_at: datetime
