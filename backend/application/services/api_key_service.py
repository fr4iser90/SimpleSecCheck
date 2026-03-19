"""
API Key Application Service (DDD).
Uses ApiKeyRepository only.
"""
from datetime import datetime, timedelta
from typing import List, Optional

from domain.entities.api_key import ApiKey
from domain.repositories.api_key_repository import ApiKeyRepository


class ApiKeyService:
    """Application service for API key operations."""

    def __init__(self, api_key_repository: ApiKeyRepository):
        self._repo = api_key_repository

    async def list_by_user(
        self,
        user_id: str,
        active_only: bool = True,
    ) -> List[ApiKey]:
        return await self._repo.list_by_user(user_id, active_only=active_only)

    async def create(
        self,
        user_id: str,
        name: str,
        key_hash: str,
        expires_in_days: Optional[int] = None,
    ) -> ApiKey:
        """Create a new API key. Caller hashes the plain key and passes key_hash."""
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        return await self._repo.create(user_id, name, key_hash, expires_at=expires_at)

    async def get_by_id(self, key_id: str, user_id: str) -> Optional[ApiKey]:
        return await self._repo.get_by_id(key_id, user_id)

    async def revoke(self, key_id: str, user_id: str) -> bool:
        return await self._repo.revoke(key_id, user_id)
