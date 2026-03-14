"""
Password Service

Handles password hashing, verification, and reset token management.
Uses Argon2 exclusively for password hashing (enterprise-grade security).
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.logging_config import get_logger
from infrastructure.database.models import User, PasswordResetToken
from config.settings import get_settings

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
        session: AsyncSession,
        user_id: str,
        expiry_hours: Optional[int] = None
    ) -> tuple[str, PasswordResetToken]:
        """
        Create a password reset token for a user.
        
        Args:
            session: Database session
            user_id: User UUID
            expiry_hours: Token expiry in hours (default from settings)
            
        Returns:
            Tuple of (plain_token, token_model)
        """
        if expiry_hours is None:
            expiry_hours = self.settings.PASSWORD_RESET_TOKEN_EXPIRY_HOURS
        
        # Generate token
        plain_token = self.generate_reset_token()
        token_hash = self.hash_token(plain_token)
        
        # Calculate expiry
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(hours=expiry_hours)
        
        # Create token record
        token_model = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash,
            created_at=created_at,
            expires_at=expires_at
        )
        
        session.add(token_model)
        await session.commit()
        await session.refresh(token_model)
        
        logger.info("Password reset token created", user_id=str(user_id))
        
        return plain_token, token_model
    
    async def verify_reset_token(
        self,
        session: AsyncSession,
        token: str
    ) -> Optional[PasswordResetToken]:
        """
        Verify and retrieve a password reset token.
        
        Args:
            session: Database session
            token: Plain text token
            
        Returns:
            Token model if valid, None otherwise
        """
        token_hash = self.hash_token(token)
        
        # Find token
        result = await session.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used_at.is_(None)
            )
        )
        token_model = result.scalar_one_or_none()
        
        if not token_model:
            return None
        
        # Check expiry
        if datetime.utcnow() > token_model.expires_at:
            logger.warning("Password reset token expired", token_id=str(token_model.id))
            return None
        
        return token_model
    
    async def mark_token_used(
        self,
        session: AsyncSession,
        token_model: PasswordResetToken
    ) -> None:
        """
        Mark a reset token as used.
        
        Args:
            session: Database session
            token_model: Token model to mark as used
        """
        token_model.used_at = datetime.utcnow()
        await session.commit()
        logger.info("Password reset token marked as used", token_id=str(token_model.id))
    
    async def get_user_by_email(
        self,
        session: AsyncSession,
        email: str
    ) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            session: Database session
            email: User email address
            
        Returns:
            User model if found, None otherwise
        """
        result = await session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def update_user_password(
        self,
        session: AsyncSession,
        user: User,
        new_password: str
    ) -> None:
        """
        Update user password.
        
        Args:
            session: Database session
            user: User model
            new_password: New plain text password
        """
        user.password_hash = self.hash_password(new_password)
        user.updated_at = datetime.utcnow()
        await session.commit()
        logger.info("User password updated", user_id=str(user.id))
