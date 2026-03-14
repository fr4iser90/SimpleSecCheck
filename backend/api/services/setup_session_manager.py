"""
Setup Session Manager

This service handles the creation, validation, and management of setup sessions
with enterprise-grade security features including IP and User-Agent binding.
"""
import json
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from infrastructure.redis.client import redis_client


class SetupSessionManager:
    """Manager for setup sessions with security bindings."""
    
    def __init__(self, session_timeout_minutes: int = 30):
        """
        Initialize SetupSessionManager.
        
        Args:
            session_timeout_minutes: Session timeout in minutes (default: 30)
        """
        self.session_timeout_minutes = session_timeout_minutes
        self.session_prefix = "setup:session:"
    
    async def create_session(self, ip: str, user_agent: str, token: str) -> str:
        """
        Create a new setup session with security bindings.
        
        Args:
            ip: Client IP address
            user_agent: Client User-Agent string
            token: Setup token used to create session
            
        Returns:
            Session ID string
        """
        session_id = secrets.token_hex(16)
        
        session_data = {
            "session_id": session_id,
            "ip": ip,
            "user_agent": user_agent,
            "token_hash": self._hash_token(token),
            "created_at": datetime.utcnow().isoformat(),
            "last_seen": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(minutes=self.session_timeout_minutes)).isoformat(),
            "current_step": 1,
            "completed_steps": [],
            "is_active": True
        }
        
        # Store session in Redis with TTL
        redis_key = f"{self.session_prefix}{session_id}"
        await redis_client.set(
            redis_key,
            json.dumps(session_data),
            expire=self.session_timeout_minutes * 60  # Convert to seconds
        )
        
        return session_id
    
    async def validate_session(self, session_id: str, ip: str, user_agent: str) -> bool:
        """
        Validate a setup session with IP and User-Agent binding.
        
        Args:
            session_id: Session ID to validate
            ip: Current client IP address
            user_agent: Current client User-Agent string
            
        Returns:
            True if session is valid, False otherwise
        """
        redis_key = f"{self.session_prefix}{session_id}"
        session_data = await redis_client.get(redis_key)
        
        if not session_data:
            return False
        
        try:
            data = json.loads(session_data)
            
            # Validate IP and User-Agent binding
            if data["ip"] != ip or data["user_agent"] != user_agent:
                return False
            
            # Validate expiration
            expires_at = datetime.fromisoformat(data["expires_at"])
            if datetime.utcnow() > expires_at:
                return False
            
            # Validate active status
            if not data.get("is_active", True):
                return False
            
            # Update last_seen for idle timeout
            data["last_seen"] = datetime.utcnow().isoformat()
            await redis_client.set(
                redis_key,
                json.dumps(data),
                expire=self.session_timeout_minutes * 60
            )
            
            return True
            
        except (json.JSONDecodeError, KeyError, ValueError):
            return False
    
    async def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data without validation.
        
        Args:
            session_id: Session ID to retrieve
            
        Returns:
            Session data dictionary or None if not found
        """
        redis_key = f"{self.session_prefix}{session_id}"
        session_data = await redis_client.get(redis_key)
        
        if not session_data:
            return None
        
        try:
            return json.loads(session_data)
        except json.JSONDecodeError:
            return None
    
    async def update_session_step(self, session_id: str, step: int) -> bool:
        """
        Update the current step in a setup session.
        
        Args:
            session_id: Session ID to update
            step: New step number
            
        Returns:
            True if updated successfully, False otherwise
        """
        redis_key = f"{self.session_prefix}{session_id}"
        session_data = await redis_client.get(redis_key)
        
        if not session_data:
            return False
        
        try:
            data = json.loads(session_data)
            data["current_step"] = step
            data["last_seen"] = datetime.utcnow().isoformat()
            
            await redis_client.set(
                redis_key,
                json.dumps(data),
                expire=self.session_timeout_minutes * 60
            )
            
            return True
            
        except (json.JSONDecodeError, KeyError):
            return False
    
    async def complete_session_step(self, session_id: str, step: int) -> bool:
        """
        Mark a step as completed in the setup session.
        
        Args:
            session_id: Session ID to update
            step: Step number to mark as completed
            
        Returns:
            True if updated successfully, False otherwise
        """
        redis_key = f"{self.session_prefix}{session_id}"
        session_data = await redis_client.get(redis_key)
        
        if not session_data:
            return False
        
        try:
            data = json.loads(session_data)
            if step not in data["completed_steps"]:
                data["completed_steps"].append(step)
            data["last_seen"] = datetime.utcnow().isoformat()
            
            await redis_client.set(
                redis_key,
                json.dumps(data),
                expire=self.session_timeout_minutes * 60
            )
            
            return True
            
        except (json.JSONDecodeError, KeyError):
            return False
    
    async def invalidate_session(self, session_id: str) -> bool:
        """
        Invalidate a setup session.
        
        Args:
            session_id: Session ID to invalidate
            
        Returns:
            True if invalidated successfully, False otherwise
        """
        redis_key = f"{self.session_prefix}{session_id}"
        await redis_client.delete(redis_key)
        return True
    
    async def extend_session(self, session_id: str) -> bool:
        """
        Extend session timeout by the configured duration.
        
        Args:
            session_id: Session ID to extend
            
        Returns:
            True if extended successfully, False otherwise
        """
        redis_key = f"{self.session_prefix}{session_id}"
        session_data = await redis_client.get(redis_key)
        
        if not session_data:
            return False
        
        try:
            data = json.loads(session_data)
            data["expires_at"] = (datetime.utcnow() + timedelta(minutes=self.session_timeout_minutes)).isoformat()
            data["last_seen"] = datetime.utcnow().isoformat()
            
            await redis_client.set(
                redis_key,
                json.dumps(data),
                expire=self.session_timeout_minutes * 60
            )
            
            return True
            
        except (json.JSONDecodeError, KeyError):
            return False
    
    async def is_session_expired(self, session_id: str) -> bool:
        """
        Check if a session has expired.
        
        Args:
            session_id: Session ID to check
            
        Returns:
            True if expired, False otherwise
        """
        redis_key = f"{self.session_prefix}{session_id}"
        session_data = await redis_client.get(redis_key)
        
        if not session_data:
            return True
        
        try:
            data = json.loads(session_data)
            expires_at = datetime.fromisoformat(data["expires_at"])
            return datetime.utcnow() > expires_at
            
        except (json.JSONDecodeError, KeyError, ValueError):
            return True
    
    async def get_session_ip(self, session_id: str) -> Optional[str]:
        """
        Get the IP address associated with a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            IP address string or None if not found
        """
        data = await self.get_session_data(session_id)
        return data.get("ip") if data else None
    
    async def get_session_user_agent(self, session_id: str) -> Optional[str]:
        """
        Get the User-Agent associated with a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            User-Agent string or None if not found
        """
        data = await self.get_session_data(session_id)
        return data.get("user_agent") if data else None
    
    def _hash_token(self, token: str) -> str:
        """
        Hash a token for session storage.
        
        Args:
            token: Plain text token
            
        Returns:
            SHA256 hash of the token
        """
        import hashlib
        return hashlib.sha256(token.encode()).hexdigest()