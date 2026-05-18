"""
Authentication Middleware

This module provides middleware for handling authentication and authorization
in the FastAPI application. Supports JWT tokens, API keys (ssc_…), and session cookies.
"""
from typing import Optional, Callable, Awaitable
from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging
import time

from api.deps.actor_context import ActorContext, ActorContextDependency
from config.settings import settings

logger = logging.getLogger("api.middleware.auth_middleware")


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware that handles JWT tokens, API keys, and session cookies.

    All bearer resolution goes through ActorContextDependency.resolve_context()
    (same logic as route dependencies).
    """

    def __init__(
        self,
        app,
        actor_context_dependency: ActorContextDependency,
        protected_paths: Optional[list] = None,
        public_paths: Optional[list] = None,
        admin_paths: Optional[list] = None,
    ):
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
        try:
            if self._is_public_path(request.url.path):
                return await call_next(request)

            if self._is_admin_path(request.url.path):
                actor_context = await self._resolve_actor_context(
                    request, require_authenticated=True
                )
                request.state.actor_context = actor_context
            elif self._is_protected_path(request.url.path):
                access_mode = getattr(settings, "ACCESS_MODE", "public")
                require_auth = access_mode not in ("public", "mixed")
                actor_context = await self._resolve_actor_context(
                    request, require_authenticated=require_auth
                )
                request.state.actor_context = actor_context
            else:
                actor_context = await self._resolve_actor_context(
                    request, require_authenticated=False
                )
                request.state.actor_context = actor_context

            return await call_next(request)

        except HTTPException:
            raise
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": f"Authentication error: {str(e)}"},
            )

    def _is_public_path(self, path: str) -> bool:
        for public_path in self.public_paths:
            if path.startswith(public_path):
                return True
        return False

    def _is_protected_path(self, path: str) -> bool:
        for protected_path in self.protected_paths:
            if path.startswith(protected_path):
                return True
        return False

    def _is_admin_path(self, path: str) -> bool:
        for admin_path in self.admin_paths:
            if path.startswith(admin_path):
                return True
        return False

    async def _resolve_actor_context(
        self,
        request: Request,
        *,
        require_authenticated: bool,
    ) -> ActorContext:
        """Resolve context via ActorContextDependency (API key, JWT, cookies, guest)."""
        credentials = self._get_credentials(request)
        dummy_response = JSONResponse(content={})
        context = await self.actor_context_dependency.resolve_context(
            request,
            dummy_response,
            credentials,
        )

        if require_authenticated and not context.is_authenticated:
            if credentials and self.actor_context_dependency._looks_like_api_key(
                credentials.credentials.strip()
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired API key",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            if not credentials:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return context

    async def _get_admin_context(self, request: Request) -> ActorContext:
        return await self._resolve_actor_context(request, require_authenticated=True)

    @staticmethod
    def _get_credentials(request: Request) -> Optional[HTTPAuthorizationCredentials]:
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:]
            return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware to prevent abuse.
    """

    def __init__(
        self,
        app,
        rate_limits: dict = None,
    ):
        super().__init__(app)
        if rate_limits is None:
            from domain.services.security_policy_service import SecurityPolicyService
            rate_limits = SecurityPolicyService.get_rate_limits()
        self.rate_limits = rate_limits
        self.request_counts = {}

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        try:
            actor_context = getattr(request.state, "actor_context", None)
            if not actor_context:
                actor_context = ActorContext()

            if await self._is_rate_limited(actor_context):
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Rate limit exceeded",
                        "retry_after": self.rate_limits[
                            self._get_user_type(actor_context)
                        ]["window"],
                    },
                )

            response = await call_next(request)
            await self._increment_request_count(actor_context)
            return response

        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": f"Rate limiting error: {str(e)}"},
            )

    def _get_user_type(self, actor_context: ActorContext) -> str:
        if not actor_context.is_authenticated:
            return "guest"
        return "authenticated"

    async def _is_rate_limited(self, actor_context: ActorContext) -> bool:
        user_type = self._get_user_type(actor_context)
        limit_config = self.rate_limits[user_type]

        user_id = actor_context.get_identifier()
        current_time = int(time.time())
        window_start = current_time - limit_config["window"]

        if user_id in self.request_counts:
            self.request_counts[user_id] = [
                ts for ts in self.request_counts[user_id] if ts > window_start
            ]

        current_count = len(self.request_counts.get(user_id, []))
        return current_count >= limit_config["requests"]

    async def _increment_request_count(self, actor_context: ActorContext) -> None:
        user_id = actor_context.get_identifier()
        current_time = int(time.time())

        if user_id not in self.request_counts:
            self.request_counts[user_id] = []

        self.request_counts[user_id].append(current_time)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Security headers middleware."""

    def __init__(self, app):
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

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

        if settings.APP_URL and str(settings.APP_URL).lower().startswith("https"):
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response
