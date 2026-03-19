"""
User Application Service (DDD).

Orchestrates user lookup and updates; uses UserRepository only.
"""
from datetime import datetime
from typing import List, Optional

from domain.entities.user import User
from domain.repositories.user_repository import UserRepository


class UserService:
    """Application service for user operations."""

    def __init__(self, user_repository: UserRepository):
        self._repo = user_repository

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by id."""
        return await self._repo.get_by_id(user_id)

    async def get_by_email(self, email: str, active_only: bool = True) -> Optional[User]:
        """Get user by email (e.g. for login)."""
        return await self._repo.get_by_email(email, active_only=active_only)

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return await self._repo.get_by_username(username)

    async def list_all(
        self, limit: int = 500, offset: int = 0, active_only: Optional[bool] = None
    ) -> List[User]:
        """List users (for admin). active_only: True=active, False=pending (awaiting approval), None=all."""
        return await self._repo.list_all(limit=limit, offset=offset, active_only=active_only)

    async def create(self, user: User) -> User:
        """Create a new user."""
        return await self._repo.create(user)

    async def update(self, user: User) -> User:
        """Update existing user."""
        return await self._repo.update(user)

    async def update_last_login(self, user_id: str) -> Optional[User]:
        """Set last_login to now and persist. Returns updated user or None."""
        user = await self._repo.get_by_id(user_id)
        if not user:
            return None
        user.last_login = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        return await self._repo.update(user)

    async def update_password(self, user_id: str, new_password_hash: str) -> Optional[User]:
        """Update password hash and persist. Returns updated user or None."""
        user = await self._repo.get_by_id(user_id)
        if not user:
            return None
        user.password_hash = new_password_hash
        user.updated_at = datetime.utcnow()
        return await self._repo.update(user)

    async def delete_by_id(self, user_id: str) -> bool:
        """Delete user by id (e.g. admin). Returns True if deleted."""
        return await self._repo.delete_by_id(user_id)
