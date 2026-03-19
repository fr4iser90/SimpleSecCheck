"""Email verification token entity."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class EmailVerificationToken:
    """Token for verifying a user's email address."""
    id: str
    user_id: str
    token_hash: str
    created_at: datetime
    expires_at: datetime
    used_at: Optional[datetime] = None
