"""
User Repository Interface (DDD port).
"""
from abc import ABC, abstractmethod
from typing import List, Optional

from domain.entities.user import User


class UserRepository(ABC):
    """Interface for user persistence."""

    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by id. Returns None if not found."""
        pass

    @abstractmethod
    async def get_by_email(self, email: str, active_only: bool = True) -> Optional[User]:
        """Get user by email. If active_only, only return when is_active is True."""
        pass

    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username. Returns None if not found."""
        pass

    @abstractmethod
    async def list_all(self, limit: int = 500, offset: int = 0) -> List[User]:
        """List all users (e.g. for admin). Order by created_at desc."""
        pass

    @abstractmethod
    async def create(self, user: User) -> User:
        """Persist a new user. Returns the created user (with id set)."""
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        """Update existing user. Raises if not found."""
        pass

    @abstractmethod
    async def delete_by_id(self, user_id: str) -> bool:
        """Delete user by id. Returns True if deleted."""
        pass

    @abstractmethod
    async def has_admin_user(self) -> bool:
        """Return True if at least one active admin user exists (for setup status)."""
        pass
