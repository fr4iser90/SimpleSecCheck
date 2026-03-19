"""
Password Service

Handles password hashing, verification, and reset token management.
Uses Argon2 exclusively for password hashing (enterprise-grade security).
Token persistence via PasswordResetTokenRepository (DDD).
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional

from infrastructure.logging_config import get_logger
from config.settings import get_settings
from domain.entities.password_reset_token import PasswordResetToken as PasswordResetTokenEntity
from domain.repositories.password_reset_token_repository import PasswordResetTokenRepository

logger = get_logger("api.services.password")

# Argon2 is required - no fallbacks
try:
    from argon2 import PasswordHasher
except ImportError:
    raise RuntimeError("Argon2 is required. Install argon2-cffi: pip install argon2-cffi")


class PasswordService:
    """Service for password hashing and verification using Argon2."""
    
    def __init__(self):
        self.settings = get_settings()
        # Use Argon2 with default settings
        # Note: PasswordPolicyService uses custom settings, but both produce compatible hashes
        self.hasher = PasswordHasher()
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using Argon2.
        
        Args:
            password: Plain text password
            
        Returns:
            Argon2 hash string (self-identifying, no prefix needed)
        """
        # Argon2 hashes are self-identifying (start with $argon2id$ or $argon2i$)
        # No prefix needed - matches PasswordPolicyService format
        return self.hasher.hash(password)
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify a password against its Argon2 hash.
        
        Args:
            password: Plain text password
            password_hash: Stored Argon2 hash (self-identifying, starts with $argon2)
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            # Argon2 hashes are self-identifying (start with $argon2id$ or $argon2i$)
            # No prefix needed - standard Argon2 format
            self.hasher.verify(password_hash, password)
            return True
        except Exception as e:
            logger.error("Password verification failed", error=str(e))
            return False
    
    def generate_reset_token(self) -> str:
        """
        Generate a secure password reset token.
        
        Returns:
            URL-safe token string
        """
        return secrets.token_urlsafe(32)  # 32 bytes = 43 characters URL-safe
    
    def hash_token(self, token: str) -> str:
        """
        Hash a reset token for storage.
        
        Args:
            token: Plain text token
            
        Returns:
            Hashed token string
        """
        return hashlib.sha256(token.encode()).hexdigest()
    
    async def create_reset_token(
        self,
        user_id: str,
        expiry_hours: Optional[int] = None
    ) -> tuple[str, PasswordResetTokenEntity]:
        """
        Create a password reset token for a user.
        
        Args:
            user_id: User UUID string
            expiry_hours: Token expiry in hours (default from settings)
            
        Returns:
            Tuple of (plain_token, token_entity)
        """
        if expiry_hours is None:
            expiry_hours = self.settings.PASSWORD_RESET_TOKEN_EXPIRY_HOURS
        
        plain_token = self.generate_reset_token()
        token_hash = self.hash_token(plain_token)
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(hours=expiry_hours)
        
        token_entity = PasswordResetTokenEntity(
            id="",
            user_id=user_id,
            token_hash=token_hash,
            created_at=created_at,
            expires_at=expires_at,
            used_at=None,
        )
        token_entity = await self._token_repo.create(token_entity)
        logger.info("Password reset token created", user_id=str(user_id))
        return plain_token, token_entity
    
    async def verify_reset_token(self, token: str) -> Optional[PasswordResetTokenEntity]:
        """
        Verify and retrieve a password reset token.
        
        Args:
            token: Plain text token
            
        Returns:
            Token entity if valid and not expired, None otherwise
        """
        token_hash = self.hash_token(token)
        token_entity = await self._token_repo.get_by_token_hash(token_hash)
        if not token_entity:
            return None
        if datetime.utcnow() > token_entity.expires_at:
            logger.warning("Password reset token expired", token_id=token_entity.id)
            return None
        return token_entity
    
    async def mark_token_used(self, token_entity: PasswordResetTokenEntity) -> None:
        """
        Mark a reset token as used.
        
        Args:
            token_entity: Token entity to mark as used
        """
        token_entity.used_at = datetime.utcnow()
        await self._token_repo.update(token_entity)
        logger.info("Password reset token marked as used", token_id=token_entity.id)
