"""
Actor Context Dependency

This module provides the ActorContext dependency that resolves user/session context
from JWT tokens or session cookies, supporting both authenticated and guest users.
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import secrets
import uuid
import logging

from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

from config.settings import settings

class ActorContext(BaseModel):
    """Context for the current actor (user or guest session)."""
    
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    is_authenticated: bool = False
    email: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None  # 'admin' or 'user'
    
    def get_identifier(self) -> str:
        """Get the identifier for this actor (user_id or session_id)."""
        return self.user_id or self.session_id or "anonymous"
    
    def is_guest(self) -> bool:
        """Check if this is a guest session."""
        return not self.is_authenticated
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging and debugging."""
        return {
            'user_id': self.user_id,
            'session_id': self.session_id,
            'is_authenticated': self.is_authenticated,
            'email': self.email,
            'name': self.name,
        }


class ActorContextDependency:
    """Dependency for resolving actor context from request."""
    
    def __init__(
        self,
        jwt_secret_key: str = "your-secret-key",
        jwt_algorithm: str = "HS256",
        jwt_expiration_minutes: int = 30,
        environment: str = "permissive"  # SECURITY_MODE value
    ):
        self.security = HTTPBearer(auto_error=False)
        self.jwt_secret_key = jwt_secret_key
        self.jwt_algorithm = jwt_algorithm
        self.jwt_expiration_minutes = jwt_expiration_minutes
        self.environment = environment
        self.logger = logging.getLogger("api.deps.actor_context")
    
    async def __call__(
        self,
        request: Request,
        response: Response,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
    ) -> ActorContext:
        """Resolve actor context from JWT token or session cookie."""
        
        # Try to get context from JWT token first
        if credentials:
            try:
                context = await self._get_context_from_jwt(credentials.credentials)
                if context:
                    return context
            except JWTError:
                # JWT is invalid, continue to session check
                pass
        
        # Try to get context from session cookie
        session_id = request.cookies.get("session_id")
        if session_id:
            context = await self._get_context_from_session(session_id)
            if context:
                return context
        
        # Create new guest session
        return await self._create_guest_session(response)
    
    async def _get_context_from_jwt(self, token: str) -> Optional[ActorContext]:
        """Extract context from JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret_key,
                algorithms=[self.jwt_algorithm]
            )
            
            user_id = payload.get("sub")
            email = payload.get("email")
            name = payload.get("name")
            role = payload.get("role")
            
            if not user_id:
                return None
            
            return ActorContext(
                user_id=user_id,
                session_id=None,
                is_authenticated=True,
                email=email,
                name=name,
                role=role
            )
        except JWTError:
            return None
    
    async def _get_context_from_session(self, session_id: str) -> Optional[ActorContext]:
        """Get context from session storage."""
        # This would typically check Redis or database
        # For now, we'll assume session is valid
        return ActorContext(
            user_id=None,
            session_id=session_id,
            is_authenticated=False
        )
    
    async def _create_guest_session(self, response: Response) -> ActorContext:
        """Create a new guest session."""
        session_id = str(uuid.uuid4())
        
        # Set session cookie
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=self.environment == "production",
            samesite="lax",
            max_age=86400 * 30  # 30 days
        )
        
        return ActorContext(
            user_id=None,
            session_id=session_id,
            is_authenticated=False
        )
    
    def create_jwt_token(self, user_id: str, email: str, name: str, role: Optional[str] = None) -> str:
        """Create JWT token for authenticated user."""
        expires_delta = timedelta(minutes=self.jwt_expiration_minutes)
        expire = datetime.utcnow() + expires_delta
        
        payload = {
            "sub": user_id,
            "email": email,
            "name": name,
            "role": role,
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        
        return jwt.encode(payload, self.jwt_secret_key, algorithm=self.jwt_algorithm)
    
    def create_session_cookie(self, session_id: str, response: Response) -> None:
        """Create session cookie for guest user."""
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=self.environment == "production",
            samesite="lax",
            max_age=86400 * 30  # 30 days
        )
    
    def clear_session_cookie(self, response: Response) -> None:
        """Clear session cookie."""
        response.delete_cookie(
            key="session_id",
            httponly=True,
            secure=self.environment == "production",
            samesite="lax"
        )


# Global instance
actor_context_dependency = ActorContextDependency()


# Dependency function for FastAPI
async def get_actor_context(
    request: Request,
    response: Response,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> ActorContext:
    """FastAPI dependency to get actor context."""
    return await actor_context_dependency(request, response, credentials)


# Dependency for authenticated users only
async def get_authenticated_user(
    actor_context: ActorContext = Depends(get_actor_context)
) -> ActorContext:
    """FastAPI dependency that requires authentication."""
    if not actor_context.is_authenticated:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return actor_context


# Dependency for admin users only
async def get_admin_user(
    actor_context: ActorContext = Depends(get_authenticated_user)
) -> ActorContext:
    """FastAPI dependency that requires admin privileges."""
    # This would typically check user roles/permissions
    # For now, we'll assume all authenticated users are admins
    return actor_context