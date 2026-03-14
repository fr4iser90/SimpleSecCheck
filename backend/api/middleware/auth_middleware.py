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
        environment: str = "development",
    ):
        """
        Initialize authentication middleware.
        
        Args:
            app: FastAPI application instance
            actor_context_dependency: Actor context dependency instance
            protected_paths: List of paths that require authentication
            public_paths: List of paths that are publicly accessible
            admin_paths: List of paths that require admin privileges
            environment: Application environment (development/production)
        """
        super().__init__(app)
        self.actor_context_dependency = actor_context_dependency
        self.protected_paths = protected_paths or []
        self.public_paths = public_paths or []
        self.admin_paths = admin_paths or []
        self.environment = environment
    
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
            # Debug: Log that middleware is being called
            logger.debug(f"AuthMiddleware dispatch called for path: {request.url.path}")
            logger.debug(f"Environment: {self.environment}")
            logger.debug(f"Auth mode: {settings.AUTH_MODE}")
            logger.debug(f"Protected paths: {self.protected_paths}")
            logger.debug(f"Public paths: {self.public_paths}")
            
            # Check if path is public (skip authentication)
            if self._is_public_path(request.url.path):
                logger.debug("Path is public, skipping authentication")
                response = await call_next(request)
                return response
            
            # Check if path requires admin privileges
            if self._is_admin_path(request.url.path):
                logger.debug("Path requires admin privileges")
                actor_context = await self._get_admin_context(request)
                request.state.actor_context = actor_context
            # Check if path requires authentication
            elif self._is_protected_path(request.url.path):
                logger.debug(f"Protected path detected: {request.url.path}")
                
                # FREE mode: Allow unauthenticated access to scans and other features
                # BASIC/JWT modes: Require authentication
                if settings.AUTH_MODE == "free":
                    logger.debug("FREE mode: Using _get_or_create_context for all paths")
                    actor_context = await self._get_or_create_context(request)
                else:
                    logger.debug(f"{settings.AUTH_MODE} mode: Using _get_authenticated_context")
                    actor_context = await self._get_authenticated_context(request)
                request.state.actor_context = actor_context
            # For other paths, create guest context if needed
            else:
                logger.debug("Using _get_or_create_context for other paths")
                actor_context = await self._get_or_create_context(request)
                request.state.actor_context = actor_context
            
            # Process request
            response = await call_next(request)
            
            # Add context to response headers for debugging
            if self.environment == "development" and request.url.path not in ["/api/v1/health", "/api/v1/docs", "/api/v1/metrics"]:
                try:
                    response.headers["X-Actor-Context"] = str(actor_context.to_dict())
                except Exception:
                    pass  # Don't fail if context serialization fails
            
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
        logger.debug("_get_or_create_context called")
        
        # Try to get context from JWT token
        credentials = await self._get_credentials(request)
        if credentials:
            logger.debug("Found JWT credentials, trying to get context from JWT")
            try:
                context = await self.actor_context_dependency._get_context_from_jwt(credentials.credentials)
                if context:
                    logger.debug("Successfully got context from JWT")
                    return context
            except Exception as e:
                logger.debug(f"Failed to get context from JWT: {e}")
                pass
        
        # Try to get context from session cookie
        session_id = request.cookies.get("session_id")
        logger.debug(f"Session ID from cookies: {session_id}")
        if session_id:
            logger.debug("Found session ID, trying to get context from session")
            try:
                context = await self.actor_context_dependency._get_context_from_session(session_id)
                if context:
                    logger.debug("Successfully got context from session")
                    return context
            except Exception as e:
                logger.debug(f"Failed to get context from session: {e}")
        
        # Create new guest session
        logger.debug("Creating new guest session")
        response = JSONResponse(content={})  # Dummy response for session creation
        try:
            context = await self.actor_context_dependency._create_guest_session(response)
            logger.debug("Successfully created guest session")
            return context
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
            rate_limits: Dictionary of rate limits per user type
        """
        super().__init__(app)
        self.rate_limits = rate_limits or {
            "guest": {"requests": 100, "window": 3600},  # 100 requests per hour for guests
            "authenticated": {"requests": 1000, "window": 3600},  # 1000 requests per hour for authenticated users
            "admin": {"requests": 5000, "window": 3600},  # 5000 requests per hour for admins
        }
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
    
    def __init__(self, app, environment: str = "development"):
        """
        Initialize security headers middleware.
        
        Args:
            app: FastAPI application instance
            environment: Application environment (development/production)
        """
        super().__init__(app)
        self.environment = environment
    
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
        
        # Add HSTS header in production
        if self.environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


# Import time at module level for rate limiting
import time