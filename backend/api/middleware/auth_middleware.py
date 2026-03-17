"""
Authentication Middleware

This module provides middleware for handling authentication and authorization
in the FastAPI application. Supports both JWT tokens and session cookies.
"""
from typing import Optional, Callable, Awaitable
from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

from api.deps.actor_context import ActorContext, ActorContextDependency
from config.settings import settings

# Create logger
logger = logging.getLogger("api.middleware.auth_middleware")


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware that handles JWT tokens and session cookies.
    
    This middleware:
    - Resolves actor context from JWT tokens or session cookies
    - Handles authentication for protected routes
    - Manages session creation for guest users
    - Provides centralized authentication logic
    """
    
    def __init__(
        self,
        app,
        actor_context_dependency: ActorContextDependency,
        protected_paths: Optional[list] = None,
        public_paths: Optional[list] = None,
        admin_paths: Optional[list] = None,
    ):
        """Initialize authentication middleware."""
        super().__init__(app)
        self.actor_context_dependency = actor_context_dependency
        self.protected_paths = protected_paths or []
        self.public_paths = public_paths or []
        self.admin_paths = admin_paths or []
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process incoming request and handle authentication.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response
        """
        try:
            # Check if path is public (skip authentication)
            if self._is_public_path(request.url.path):
                response = await call_next(request)
                return response

            # Check if path requires admin privileges
            if self._is_admin_path(request.url.path):
                actor_context = await self._get_admin_context(request)
                request.state.actor_context = actor_context
            # Check if path requires authentication when ACCESS_MODE=private
            elif self._is_protected_path(request.url.path):
                access_mode = getattr(settings, "ACCESS_MODE", "public")
                if access_mode in ("public", "mixed"):
                    actor_context = await self._get_or_create_context(request)
                else:
                    actor_context = await self._get_authenticated_context(request)
                request.state.actor_context = actor_context
            # For other paths, create guest context if needed
            else:
                actor_context = await self._get_or_create_context(request)
                request.state.actor_context = actor_context
            
            response = await call_next(request)
            return response
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            # Handle unexpected errors
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": f"Authentication error: {str(e)}"}
            )
    
    def _is_public_path(self, path: str) -> bool:
        """Check if path is publicly accessible."""
        for public_path in self.public_paths:
            if path.startswith(public_path):
                return True
        return False
    
    def _is_protected_path(self, path: str) -> bool:
        """Check if path requires authentication."""
        for protected_path in self.protected_paths:
            if path.startswith(protected_path):
                return True
        return False
    
    def _is_admin_path(self, path: str) -> bool:
        """Check if path requires admin privileges."""
        for admin_path in self.admin_paths:
            if path.startswith(admin_path):
                return True
        return False
    
    async def _get_or_create_context(self, request: Request) -> ActorContext:
        """Get existing context or create new guest session."""
        # Try to get context from JWT token
        credentials = await self._get_credentials(request)
        if credentials:
            try:
                context = await self.actor_context_dependency._get_context_from_jwt(credentials.credentials)
                if context:
                    return context
            except Exception:
                pass

        # Try to get context from session cookie
        session_id = request.cookies.get("session_id")
        if session_id:
            try:
                context = await self.actor_context_dependency._get_context_from_session(session_id)
                if context:
                    return context
            except Exception:
                pass

        # Create new guest session
        response = JSONResponse(content={})  # Dummy response for session creation
        try:
            return await self.actor_context_dependency._create_guest_session(response)
        except Exception as e:
            logger.error(f"Failed to create guest session: {e}")
            raise
    
    async def _get_authenticated_context(self, request: Request) -> ActorContext:
        """Get authenticated user context or raise 401."""
        credentials = await self._get_credentials(request)
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        try:
            context = await self.actor_context_dependency._get_context_from_jwt(credentials.credentials)
            if not context or not context.is_authenticated:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return context
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    async def _get_admin_context(self, request: Request) -> ActorContext:
        """Get admin user context or raise 403."""
        context = await self._get_authenticated_context(request)
        
        # For now, assume all authenticated users are admins
        # In production, check user roles/permissions
        return context
    
    async def _get_credentials(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        """Extract JWT credentials from request headers."""
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:]  # Remove "Bearer " prefix
            return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware to prevent abuse.
    
    This middleware:
    - Tracks request rates per user/session
    - Implements configurable rate limits
    - Returns appropriate error responses when limits are exceeded
    """
    
    def __init__(
        self,
        app,
        rate_limits: dict = None,
    ):
        """
        Initialize rate limiting middleware.
        
        Args:
            app: FastAPI application instance
            rate_limits: Dictionary of rate limits per user type (optional, uses SecurityPolicyService if not provided)
        """
        super().__init__(app)
        if rate_limits is None:
            from domain.services.security_policy_service import SecurityPolicyService
            rate_limits = SecurityPolicyService.get_rate_limits()
        self.rate_limits = rate_limits
        self.request_counts = {}  # In-memory storage (use Redis in production)
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process incoming request and check rate limits.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response
        """
        try:
            # Get actor context
            actor_context = getattr(request.state, 'actor_context', None)
            if not actor_context:
                # Create temporary context for rate limiting
                actor_context = await self._get_or_create_context(request)
            
            # Check rate limits
            if await self._is_rate_limited(actor_context):
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Rate limit exceeded",
                        "retry_after": self.rate_limits[actor_context.get_user_type()]["window"]
                    }
                )
            
            # Process request
            response = await call_next(request)
            
            # Update request count
            await self._increment_request_count(actor_context)
            
            return response
            
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": f"Rate limiting error: {str(e)}"}
            )
    
    def _get_user_type(self, actor_context: ActorContext) -> str:
        """Determine user type for rate limiting."""
        if not actor_context.is_authenticated:
            return "guest"
        # In production, check user roles
        return "authenticated"
    
    async def _is_rate_limited(self, actor_context: ActorContext) -> bool:
        """Check if user has exceeded rate limits."""
        user_type = self._get_user_type(actor_context)
        limit_config = self.rate_limits[user_type]
        
        user_id = actor_context.get_identifier()
        current_time = int(time.time())
        window_start = current_time - limit_config["window"]
        
        # Clean old entries
        if user_id in self.request_counts:
            self.request_counts[user_id] = [
                timestamp for timestamp in self.request_counts[user_id]
                if timestamp > window_start
            ]
        
        # Check current count
        current_count = len(self.request_counts.get(user_id, []))
        return current_count >= limit_config["requests"]
    
    async def _increment_request_count(self, actor_context: ActorContext) -> None:
        """Increment request count for user."""
        user_id = actor_context.get_identifier()
        current_time = int(time.time())
        
        if user_id not in self.request_counts:
            self.request_counts[user_id] = []
        
        self.request_counts[user_id].append(current_time)
    
    async def _get_or_create_context(self, request: Request) -> ActorContext:
        """Get existing context or create new guest session."""
        # Try to get context from JWT token
        credentials = await self._get_credentials(request)
        if credentials:
            try:
                context = await self.actor_context_dependency._get_context_from_jwt(credentials.credentials)
                if context:
                    return context
            except Exception:
                pass
        
        # Try to get context from session cookie
        session_id = request.cookies.get("session_id")
        if session_id:
            context = await self.actor_context_dependency._get_context_from_session(session_id)
            if context:
                return context
        
        # Create new guest session
        response = JSONResponse(content={})  # Dummy response for session creation
        return await self.actor_context_dependency._create_guest_session(response)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Security headers middleware to enhance application security.
    
    This middleware adds security headers to all responses:
    - Content Security Policy
    - X-Frame-Options
    - X-Content-Type-Options
    - X-XSS-Protection
    - Strict-Transport-Security
    """
    
    def __init__(self, app):
        """Initialize security headers middleware."""
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process incoming request and add security headers.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response with security headers
        """
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Add CSP header (adjust based on your needs)
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp_policy
        
        # HSTS when app is served over HTTPS (from APP_URL)
        if settings.APP_URL and str(settings.APP_URL).lower().startswith("https"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


# Import time at module level for rate limiting
import time