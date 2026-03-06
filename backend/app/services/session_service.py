"""
Session Management Service
Handles session creation, validation, and rate limiting
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.database import get_database


class SessionService:
    """Service for managing user sessions"""
    
    def __init__(self):
        self.db = get_database()
        from app.services.policy_service import get_policy_config
        self.policy_config = get_policy_config()
    
    async def initialize(self):
        """Initialize database connection"""
        await self.db.initialize()
    
    async def close(self):
        """Close database connection"""
        await self.db.close()
    
    async def get_or_create_session(self, request: Request) -> str:
        """
        Get existing session or create new one
        Supports both Cookie and Header (Hybrid approach)
        """
        # Try to get session from cookie first, then header
        session_id = request.cookies.get(self.policy_config.session_cookie_name)
        if not session_id:
            session_id = request.headers.get(self.policy_config.session_header_name)
        
        # Validate existing session
        if session_id:
            session = await self.db.get_session(session_id)
            if session:
                expires_at = datetime.fromisoformat(session["expires_at"])
                if expires_at > datetime.utcnow():
                    # Valid session
                    return session_id
                else:
                    # Expired session, delete it
                    await self.db.delete_session(session_id)
        
        # Create new session
        session_id = str(uuid.uuid4())
        ip_address = request.client.host if request.client else None
        
        await self.db.create_session(session_id, ip_address)
        
        return session_id
    
    async def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Validate session and return session data if valid"""
        if not session_id:
            return None
        
        session = await self.db.get_session(session_id)
        if not session:
            return None
        
        expires_at = datetime.fromisoformat(session["expires_at"])
        if expires_at <= datetime.utcnow():
            # Expired
            await self.db.delete_session(session_id)
            return None
        
        return session
    
    async def increment_scan_count(self, session_id: str) -> bool:
        """Increment scan count for rate limiting"""
        session = await self.db.get_session(session_id)
        if not session:
            return False
        
        scans_requested = session.get("scans_requested", 0) + 1
        return await self.db.update_session(session_id, scans_requested=scans_requested)
    
    async def check_rate_limit(self, session_id: str, ip_address: Optional[str] = None) -> tuple[bool, Optional[str]]:
        """
        Check if session has exceeded rate limits
        Returns (allowed, error_message)
        """
        session = await self.db.get_session(session_id)
        if not session:
            return False, "Invalid session"
        
        now = datetime.utcnow()
        last_reset = session.get("last_rate_limit_reset")
        if last_reset:
            try:
                last_reset_dt = datetime.fromisoformat(last_reset)
            except ValueError:
                last_reset_dt = None
        else:
            last_reset_dt = None

        # Initialize/reset window if needed
        if not last_reset_dt or (now - last_reset_dt).total_seconds() >= 3600:
            await self.db.update_session(
                session_id,
                scans_requested=0,
                last_rate_limit_reset=now,
            )
            session["scans_requested"] = 0
            session["last_rate_limit_reset"] = now.isoformat()

        # Check session rate limits
        scans_requested = session.get("scans_requested", 0)
        rate_limit_scans = session.get("rate_limit_scans", 10)
        
        if scans_requested >= rate_limit_scans:
            return False, f"Rate limit exceeded: {scans_requested}/{rate_limit_scans} scans per hour"
        
        # TODO: Add IP-based rate limiting if needed
        # This would require tracking IP addresses separately
        
        return True, None
    
    def set_session_cookie(self, response: Response, session_id: str):
        """Set session cookie in response"""
        max_age = self.policy_config.session_duration
        secure_cookie = self.policy_config.cookie_secure

        response.set_cookie(
            key=self.policy_config.session_cookie_name,
            value=session_id,
            max_age=max_age,
            httponly=self.policy_config.session_cookie_httponly,
            secure=secure_cookie,
            samesite=self.policy_config.cookie_samesite,
        )
    
    def set_session_header(self, response: Response, session_id: str):
        """Set session header in response"""
        response.headers[self.policy_config.session_header_name] = session_id


# Global session service instance
_session_service: Optional[SessionService] = None


async def get_session_service() -> SessionService:
    """Get or create session service instance"""
    global _session_service
    if _session_service is None:
        _session_service = SessionService()
        await _session_service.initialize()
    # Ensure database is initialized (connection pool exists)
    if hasattr(_session_service.db, 'connection_pool') and _session_service.db.connection_pool is None:
        await _session_service.initialize()
    return _session_service


async def session_middleware(request: Request, call_next):
    """
    FastAPI middleware for session management
    Handles session creation/validation and sets session in response
    """
    session_service = await get_session_service()
    
    # Get or create session
    session_id = await session_service.get_or_create_session(request)
    
    # Validate session
    session = await session_service.validate_session(session_id)
    if not session:
        # Create new session if validation failed
        session_id = str(uuid.uuid4())
        ip_address = request.client.host if request.client else None
        await session_service.db.create_session(session_id, ip_address)
    
    # Add session_id to request state
    request.state.session_id = session_id
    
    # Process request
    response = await call_next(request)
    
    # Set session in response (both cookie and header)
    session_service.set_session_cookie(response, session_id)
    session_service.set_session_header(response, session_id)
    
    return response
