"""API Key entity (value for repository return)."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ApiKey:
    """API key (hashed storage; plain key only at creation)."""
    id: str
    user_id: str
    name: str
    key_hash: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
