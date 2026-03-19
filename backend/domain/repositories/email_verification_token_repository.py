"""Email verification token repository interface (DDD port)."""
from abc import ABC, abstractmethod
from typing import Optional

from domain.entities.email_verification_token import EmailVerificationToken


class EmailVerificationTokenRepository(ABC):
    """Interface for email verification token persistence."""

    @abstractmethod
    async def create(self, token: EmailVerificationToken) -> EmailVerificationToken:
        """Persist a new token. Returns entity with id set."""
        pass

    @abstractmethod
    async def get_by_token_hash(self, token_hash: str) -> Optional[EmailVerificationToken]:
        """Get token by hash. Only returns if used_at is None."""
        pass

    @abstractmethod
    async def update(self, token: EmailVerificationToken) -> EmailVerificationToken:
        """Update token (e.g. set used_at)."""
        pass
