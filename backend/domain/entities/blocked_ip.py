"""Blocked IP entity for abuse protection."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class BlockedIP:
    """Blocked IP record."""
    id: str
    ip_address: str
    reason: Optional[str]
    blocked_by: Optional[str]
    blocked_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
