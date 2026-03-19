"""Password reset token repository interface (DDD port)."""
from abc import ABC, abstractmethod
from typing import Optional

from domain.entities.password_reset_token import PasswordResetToken


class PasswordResetTokenRepository(ABC):
    """Interface for password reset token persistence."""

    @abstractmethod
    async def create(self, token: PasswordResetToken) -> PasswordResetToken:
        """Persist a new token. Returns entity with id set."""
        pass

    @abstractmethod
    async def get_by_token_hash(self, token_hash: str) -> Optional[PasswordResetToken]:
        """Get token by hash. Only returns if used_at is None."""
        pass

    @abstractmethod
    async def update(self, token: PasswordResetToken) -> PasswordResetToken:
        """Update token (e.g. set used_at)."""
        pass
