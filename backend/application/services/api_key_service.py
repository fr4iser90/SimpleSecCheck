"""
API Key Application Service (DDD).
Uses ApiKeyRepository only.
"""
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from domain.entities.api_key import ApiKey
from domain.entities.user import User
from domain.repositories.api_key_repository import ApiKeyRepository
from domain.repositories.user_repository import UserRepository


class ApiKeyService:
    """Application service for API key operations."""

    def __init__(
        self,
        api_key_repository: ApiKeyRepository,
        user_repository: Optional[UserRepository] = None,
    ):
        self._repo = api_key_repository
        self._user_repo = user_repository

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

    async def authenticate(self, key_hash: str) -> Optional[Tuple[ApiKey, User]]:
        """
        Validate API key hash; return key + user if valid.
        Returns None if key or user is invalid, inactive, or expired.
        """
        if not self._user_repo:
            return None
        key = await self._repo.get_by_key_hash(key_hash)
        if not key:
            return None
        if key.expires_at and key.expires_at < datetime.utcnow():
            return None
        user = await self._user_repo.get_by_id(key.user_id)
        if not user or not user.is_active:
            return None
        # Throttle last_used_at updates (at most once per minute)
        touch = True
        if key.last_used_at:
            elapsed = (datetime.utcnow() - key.last_used_at).total_seconds()
            touch = elapsed >= 60
        if touch:
            await self._repo.touch_last_used(key.id)
        return key, user
