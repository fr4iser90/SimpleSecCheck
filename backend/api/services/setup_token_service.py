"""
Setup Token Service

This service handles the generation, verification, and management of setup tokens
for the Enterprise-grade Setup Security System.
Uses SystemStateRepository (DDD).
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from domain.repositories.system_state_repository import SystemStateRepository


class SetupTokenService:
    """Service for managing setup tokens with enterprise security features."""

    def __init__(self, ttl_hours: int = 24, system_state_repository: Optional["SystemStateRepository"] = None):
        self.ttl_hours = ttl_hours
        self._system_state_repository = system_state_repository
    
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
        if not token_hash or not token_created_at:
            return False

        # Check TTL using token_created_at (not last_attempt)
        expiry = token_created_at + timedelta(hours=self.ttl_hours)
        now = datetime.utcnow()
        if now > expiry:
            return False

        # Constant-time comparison to prevent timing attacks
        computed_hash = hashlib.sha256(token.encode()).hexdigest()
        return hmac.compare_digest(computed_hash, token_hash)
    
    def _get_repo(self):
        if self._system_state_repository is not None:
            return self._system_state_repository
        from infrastructure.container import get_system_state_repository
        return get_system_state_repository()

    async def store_setup_token(self, token_hash: str, created_at: datetime) -> bool:
        """Store setup token hash via SystemStateRepository."""
        try:
            repo = self._get_repo()
            if not await repo.table_exists():
                return False
            state = await repo.get_singleton()
            if not state:
                from domain.entities.system_state import SystemState
                state = SystemState()
            state.generate_setup_token(token_hash, created_at)
            await repo.save(state)
            return True
        except Exception as e:
            if "does not exist" not in str(e) and "relation" not in str(e).lower():
                print(f"Error storing setup token: {e}")
            return False
    
    async def invalidate_setup_token(self) -> bool:
        """Invalidate setup token via SystemStateRepository."""
        try:
            repo = self._get_repo()
            state = await repo.get_singleton()
            if state:
                state.invalidate_setup_token()
                await repo.save(state)
            return True
        except Exception as e:
            print(f"Error invalidating setup token: {e}")
            return False
    
    async def get_setup_token_info(self) -> Optional[dict]:
        """Get current setup token information via SystemStateRepository."""
        try:
            repo = self._get_repo()
            state = await repo.get_singleton()
            if state and state.setup_token_hash:
                return {"token_hash": state.setup_token_hash, "created_at": state.setup_token_created_at}
            return None
        except Exception as e:
            print(f"Error getting setup token info: {e}")
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