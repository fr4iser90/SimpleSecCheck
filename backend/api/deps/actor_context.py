"""
Actor Context Dependency

This module provides the ActorContext dependency that resolves user/session context
from JWT tokens or session cookies, supporting both authenticated and guest users.
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import time
import uuid

from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from pydantic import BaseModel

from config.settings import settings

def _iso_exp(exp_ts: Optional[float]) -> Optional[str]:
    """JWT exp claim to ISO-8601 UTC string."""
    if exp_ts is None:
        return None
    try:
        return datetime.utcfromtimestamp(int(exp_ts)).isoformat() + "Z"
    except (TypeError, ValueError, OSError):
        return None


class ActorContext(BaseModel):
    """Context for the current actor (user or guest session)."""
    
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    is_authenticated: bool = False
    email: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None  # 'admin' or 'user'
    expires_at: Optional[str] = None  # Access/refresh/session expiry (ISO UTC)
    
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
        jwt_secret_key: str = "",  # Must be set via constructor (e.g. from settings); empty = fail-safe
        jwt_algorithm: str = "HS256",
        jwt_expiration_minutes: int = 30,
    ):
        self.security = HTTPBearer(auto_error=False)
        self.jwt_secret_key = jwt_secret_key
        self.jwt_algorithm = jwt_algorithm
        self.jwt_expiration_minutes = jwt_expiration_minutes
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
            except jwt.PyJWTError:
                # JWT is invalid, continue to session check
                pass

        # Try refresh_token cookie (for /auth/refresh and page reload session restore)
        refresh_token = request.cookies.get("refresh_token")
        if refresh_token:
            context = self.get_context_from_refresh_token(refresh_token)
            if context:
                return context
        
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
                role=role,
                expires_at=_iso_exp(payload.get("exp")),
            )
        except jwt.PyJWTError:
            return None
    
    async def _get_context_from_session(self, session_id: str) -> Optional[ActorContext]:
        """Guest session: Redis revoked flag + issued-at for /session expires_at."""
        if not session_id or len(session_id) > 128:
            return None
        guest_exp: Optional[str] = None
        try:
            from infrastructure.redis.client import redis_client
            from infrastructure.redis.guest_session_keys import (
                issued_key,
                revoked_key,
                TTL_SECONDS,
            )

            if await redis_client.get(revoked_key(session_id)):
                return None
            issued_raw = await redis_client.get(issued_key(session_id))
            if issued_raw:
                try:
                    issued = int(issued_raw)
                    guest_exp = (
                        datetime.utcfromtimestamp(issued + TTL_SECONDS).isoformat() + "Z"
                    )
                except (TypeError, ValueError):
                    pass
        except Exception:
            self.logger.warning(
                "Guest session Redis lookup failed; treating as unissued guest",
                exc_info=True,
            )
        return ActorContext(
            user_id=None,
            session_id=session_id,
            is_authenticated=False,
            expires_at=guest_exp,
        )
    
    async def _create_guest_session(self, response: Response) -> ActorContext:
        """Create guest session: cookie + Redis issued (admin can revoke)."""
        session_id = str(uuid.uuid4())
        now = int(time.time())
        from infrastructure.redis.guest_session_keys import TTL_SECONDS

        try:
            from infrastructure.redis.client import redis_client
            from infrastructure.redis.guest_session_keys import issued_key

            await redis_client.set(
                issued_key(session_id), str(now), expire=TTL_SECONDS
            )
        except Exception:
            self.logger.debug("Guest issued-at not stored in Redis", exc_info=True)

        guest_exp = datetime.utcfromtimestamp(now + TTL_SECONDS).isoformat() + "Z"
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=self._cookie_secure(),
            samesite="lax",
            max_age=86400 * 30,
        )
        return ActorContext(
            user_id=None,
            session_id=session_id,
            is_authenticated=False,
            expires_at=guest_exp,
        )
    
    def create_jwt_token(self, user_id: str, email: str, name: str, role: Optional[str] = None) -> str:
        """Create JWT access token for authenticated user."""
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

    # Refresh token: longer-lived, stored in HttpOnly cookie only (not sent to JS)
    REFRESH_TOKEN_DAYS = 7

    def create_refresh_token(self, user_id: str, email: str, name: str, role: Optional[str] = None) -> str:
        """Create JWT refresh token (for HttpOnly cookie). Same claims, longer expiry."""
        expires_delta = timedelta(days=self.REFRESH_TOKEN_DAYS)
        expire = datetime.utcnow() + expires_delta
        payload = {
            "sub": user_id,
            "email": email,
            "name": name,
            "role": role,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
        }
        return jwt.encode(payload, self.jwt_secret_key, algorithm=self.jwt_algorithm)

    def get_context_from_refresh_token(self, token: str) -> Optional[ActorContext]:
        """Decode refresh token and return ActorContext. Returns None if invalid."""
        try:
            payload = jwt.decode(token, self.jwt_secret_key, algorithms=[self.jwt_algorithm])
            if payload.get("type") != "refresh":
                return None
            return ActorContext(
                user_id=payload.get("sub"),
                session_id=None,
                is_authenticated=True,
                email=payload.get("email"),
                name=payload.get("name"),
                role=payload.get("role"),
                expires_at=_iso_exp(payload.get("exp")),
            )
        except jwt.PyJWTError:
            return None

    def _cookie_secure(self) -> bool:
        """Secure flag for cookies: True when APP_URL is HTTPS (always secure when using HTTPS)."""
        url = (getattr(settings, "APP_URL", "") or "").strip().lower()
        return url.startswith("https://")

    def set_refresh_cookie(self, response: Response, refresh_token: str) -> None:
        """Set HttpOnly cookie with refresh token (Secure when HTTPS, SameSite=Strict)."""
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=self._cookie_secure(),
            samesite="strict",
            max_age=self.REFRESH_TOKEN_DAYS * 86400,
            path="/",
        )

    def clear_refresh_cookie(self, response: Response) -> None:
        """Clear refresh token cookie."""
        response.delete_cookie(
            key="refresh_token",
            httponly=True,
            secure=self._cookie_secure(),
            samesite="strict",
            path="/",
        )

    def create_session_cookie(self, session_id: str, response: Response) -> None:
        """Create session cookie for guest user."""
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=self._cookie_secure(),
            samesite="lax",
            max_age=86400 * 30  # 30 days
        )
    
    def clear_session_cookie(self, response: Response) -> None:
        """Clear session cookie."""
        response.delete_cookie(
            key="session_id",
            httponly=True,
            secure=self._cookie_secure(),
            samesite="lax",
            path="/",
        )


def get_actor_context_dependency(request: Request) -> ActorContextDependency:
    """Return the app's ActorContextDependency (with JWT key). Routes must use Depends(get_actor_context_dependency)."""
    return request.app.state.actor_context_dependency


# Dependency function for FastAPI
async def get_actor_context(
    request: Request,
    response: Response,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> ActorContext:
    """FastAPI dependency to get actor context."""
    return await request.app.state.actor_context_dependency(request, response, credentials)


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