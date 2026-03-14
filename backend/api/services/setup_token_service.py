"""
Setup Token Service

This service handles the generation, verification, and management of setup tokens
for the Enterprise-grade Setup Security System.
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from infrastructure.database.models import SystemState, SetupStatusEnum
from infrastructure.database.adapter import db_adapter


class SetupTokenService:
    """Service for managing setup tokens with enterprise security features."""
    
    def __init__(self, ttl_hours: int = 24):
        """
        Initialize SetupTokenService.
        
        Args:
            ttl_hours: Token time-to-live in hours (default: 24)
        """
        self.ttl_hours = ttl_hours
    
    def generate_token(self) -> str:
        """
        Generate a cryptographically secure setup token.
        
        Returns:
            256-bit secure token as hex string
        """
        # Generate 32 bytes = 256 bits entropy
        return secrets.token_hex(32)
    
    def hash_token(self, token: str) -> str:
        """
        Hash a token using SHA256 for secure storage.
        
        Args:
            token: Plain text token
            
        Returns:
            SHA256 hash of the token
        """
        return hashlib.sha256(token.encode()).hexdigest()
    
    def verify_token_secure(self, token: str, token_hash: str, token_created_at: datetime) -> bool:
        """
        Verify a setup token with constant-time comparison and TTL validation.
        
        Args:
            token: Plain text token to verify
            token_hash: Stored hash of the original token
            token_created_at: When the token was created
            
        Returns:
            True if token is valid, False otherwise
        """
        print(f"[DEBUG verify_token_secure] token_hash is None: {token_hash is None}, token_created_at is None: {token_created_at is None}")
        if not token_hash or not token_created_at:
            print(f"[DEBUG verify_token_secure] Early return False: token_hash={bool(token_hash)}, token_created_at={bool(token_created_at)}")
            return False
        
        # Check TTL using token_created_at (not last_attempt)
        expiry = token_created_at + timedelta(hours=self.ttl_hours)
        now = datetime.utcnow()
        print(f"[DEBUG verify_token_secure] TTL check: created_at={token_created_at}, expiry={expiry}, now={now}, expired={now > expiry}")
        if now > expiry:
            print(f"[DEBUG verify_token_secure] Token expired")
            return False
        
        # Constant-time comparison to prevent timing attacks
        computed_hash = hashlib.sha256(token.encode()).hexdigest()
        hash_match = hmac.compare_digest(computed_hash, token_hash)
        print(f"[DEBUG verify_token_secure] Hash comparison: computed_hash[:16]={computed_hash[:16]}..., stored_hash[:16]={token_hash[:16]}..., match={hash_match}")
        return hash_match
    
    async def store_setup_token(self, token_hash: str, created_at: datetime) -> bool:
        """
        Store setup token hash in the database.
        
        Args:
            token_hash: Hashed token to store
            created_at: When the token was created
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            # Check if system_state table exists
            if not await db_adapter.check_table_exists("system_state"):
                # Table doesn't exist yet - this is expected during initial setup
                return False
            
            session = await db_adapter.get_session()
            async with session:
                # Get or create system state (singleton - only one record should exist)
                result = await session.execute(
                    select(SystemState).limit(1)
                )
                system_state = result.scalar_one_or_none()
                
                if not system_state:
                    # Create new system state
                    system_state = SystemState()
                    system_state.setup_token_hash = token_hash
                    system_state.setup_token_created_at = created_at
                    system_state.setup_status = SetupStatusEnum.TOKEN_GENERATED
                    system_state.updated_at = datetime.utcnow()
                    session.add(system_state)
                else:
                    # Update existing system state
                    system_state.setup_token_hash = token_hash
                    system_state.setup_token_created_at = created_at
                    system_state.setup_status = SetupStatusEnum.TOKEN_GENERATED
                    system_state.updated_at = datetime.utcnow()
                
                await session.commit()
                print(f"[DEBUG store_setup_token] Token stored successfully: hash[:16]={token_hash[:16]}..., created_at={created_at}, system_state.id={system_state.id if hasattr(system_state, 'id') else 'N/A'}")
                return True
                
        except Exception as e:
            # Only log if it's not a "table does not exist" error
            if "does not exist" not in str(e) and "relation" not in str(e).lower():
                print(f"Error storing setup token: {e}")
            print(f"[DEBUG store_setup_token] Failed to store token: {e}")
            return False
    
    async def invalidate_setup_token(self) -> bool:
        """
        Invalidate setup token by removing it from the database.
        
        Returns:
            True if invalidated successfully, False otherwise
        """
        try:
            session = await db_adapter.get_session()
            async with session:
                # Get system state (singleton - only one record should exist)
                result = await session.execute(
                    select(SystemState).limit(1)
                )
                system_state = result.scalar_one_or_none()
                
                if system_state:
                    system_state.setup_token_hash = None
                    system_state.setup_token_created_at = None
                    system_state.updated_at = datetime.utcnow()
                    await session.commit()
                
                return True
                
        except Exception as e:
            print(f"Error invalidating setup token: {e}")
            return False
    
    async def get_setup_token_info(self) -> Optional[dict]:
        """
        Get current setup token information from database.
        
        Returns:
            Dictionary with token_hash and created_at, or None if not found
        """
        try:
            session = await db_adapter.get_session()
            async with session:
                # Get system state (singleton - only one record should exist)
                result = await session.execute(
                    select(SystemState).limit(1)
                )
                system_state = result.scalar_one_or_none()
                
                print(f"[DEBUG get_setup_token_info] system_state exists: {system_state is not None}")
                if system_state:
                    print(f"[DEBUG get_setup_token_info] setup_token_hash exists: {system_state.setup_token_hash is not None}, created_at: {system_state.setup_token_created_at}")
                
                if system_state and system_state.setup_token_hash:
                    result_dict = {
                        "token_hash": system_state.setup_token_hash,
                        "created_at": system_state.setup_token_created_at
                    }
                    print(f"[DEBUG get_setup_token_info] Returning token info: hash[:16]={result_dict['token_hash'][:16]}..., created_at={result_dict['created_at']}")
                    return result_dict
                
                print(f"[DEBUG get_setup_token_info] Returning None (no token found)")
                return None
                
        except Exception as e:
            print(f"Error getting setup token info: {e}")
            print(f"[DEBUG get_setup_token_info] Exception: {e}")
            return None
    
    async def is_token_expired(self, token_created_at: datetime) -> bool:
        """
        Check if a token has expired based on its creation time.
        
        Args:
            token_created_at: When the token was created
            
        Returns:
            True if expired, False otherwise
        """
        expiry = token_created_at + timedelta(hours=self.ttl_hours)
        return datetime.utcnow() > expiry
    
    def log_token_generation(self, token: str):
        """
        Log token generation for audit purposes.
        
        Args:
            token: The generated token (will be logged to stdout only)
        """
        print(f"\n=== SETUP TOKEN ===")
        print(f"Setup Token: {token}")
        print(f"Expires in: {self.ttl_hours} hours")
        print(f"Use this token in the setup wizard.")
        print(f"==================\n")