"""Password reset token entity."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class PasswordResetToken:
    """Password reset token for a user."""
    id: str
    user_id: str
    token_hash: str
    created_at: datetime
    expires_at: datetime
    used_at: Optional[datetime] = None
