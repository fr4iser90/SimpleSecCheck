"""API Key Repository Interface (DDD port)."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from domain.entities.api_key import ApiKey


class ApiKeyRepository(ABC):
    """Interface for API key persistence."""

    @abstractmethod
    async def list_by_user(
        self,
        user_id: str,
        active_only: bool = True,
    ) -> List[ApiKey]:
        """List API keys for user, newest first."""
        pass

    @abstractmethod
    async def create(
        self,
        user_id: str,
        name: str,
        key_hash: str,
        expires_at: Optional[datetime] = None,
    ) -> ApiKey:
        """Create a new API key. Returns the created key (with id)."""
        pass

    @abstractmethod
    async def get_by_id(self, key_id: str, user_id: str) -> Optional[ApiKey]:
        """Get API key by id; must belong to user."""
        pass

    @abstractmethod
    async def revoke(self, key_id: str, user_id: str) -> bool:
        """Soft-delete (set is_active=False). Returns True if found and revoked."""
        pass
