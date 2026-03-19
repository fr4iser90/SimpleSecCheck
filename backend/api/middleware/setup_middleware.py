"""
Setup Middleware

This middleware checks if system setup is required and redirects users to the setup wizard.
It ensures that users cannot access the main application until initial setup is completed.
"""
from typing import Optional, Callable, Awaitable
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from config.settings import settings
from infrastructure.redis.client import redis_client
from infrastructure.container import get_setup_status_service

# Create logger
logger = logging.getLogger("api.middleware.setup_middleware")


class SetupMiddleware(BaseHTTPMiddleware):
    """
    Middleware that handles setup requirements and redirects.
    
    This middleware:
    - Checks if setup is required on application startup
    - Redirects users to setup wizard when needed
    - Allows access to setup endpoints during setup phase
    - Blocks access to main application until setup is complete
    """
    
    def __init__(self, app):
        """Initialize setup middleware."""
        super().__init__(app)
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process incoming request and handle setup requirements.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response
        """
        try:
            # Skip setup check for setup endpoints
            if self._is_setup_endpoint(request.url.path):
                return await call_next(request)
            
            # Skip setup check for health checks and frontend config
            if request.url.path in ["/api/health", "/api/info", "/metrics", "/api/config"]:
                return await call_next(request)
            
            # Check if setup is required
            if await self._is_setup_required():
                # Redirect to setup page
                if self._is_api_request(request):
                    return JSONResponse(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        content={
                            "error": "Setup required",
                            "message": "System setup is required. Please complete the setup wizard.",
                            "setup_url": "/setup",
                            "api_url": "/api/setup/status"
                        }
                    )
                else:
                    # Redirect to setup page for web requests
                    return RedirectResponse(url="/setup")
            
            # Setup not required, continue with request
            return await call_next(request)
            
        except Exception as e:
            logger.error(f"Setup middleware error: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": f"Setup check failed: {str(e)}"}
            )
    
    def _is_setup_endpoint(self, path: str) -> bool:
        """Check if path is a setup endpoint."""
        setup_paths = [
            "/api/setup",
            "/setup",
            "/api/setup/status",
            "/api/setup/initialize",
            "/api/setup/health",
            "/api/config",  # Frontend config needed during setup
        ]
        return any(path.startswith(setup_path) for setup_path in setup_paths)
    
    def _is_api_request(self, request: Request) -> bool:
        """Check if request is an API request."""
        # Check for API-specific headers
        accept_header = request.headers.get("Accept", "")
        content_type = request.headers.get("Content-Type", "")
        
        # API requests typically have these characteristics
        is_api_accept = "application/json" in accept_header or "application/xml" in accept_header
        is_api_content = "application/json" in content_type or "application/xml" in content_type
        is_ajax = request.headers.get("X-Requested-With", "").lower() == "xmlhttprequest"
        
        return is_api_accept or is_api_content or is_ajax
    
    async def _is_setup_required(self) -> bool:
        """
        Check if setup is required (reads from DB every request).
        When USE_CASE is solo and DB is not connected, allow skip so UI can load.
        """
        try:
            setup_status = await get_setup_status_service().get_setup_status()
            if setup_status.get("setup_complete", False):
                return False
            if settings.USE_CASE == "solo" and not setup_status.get("database_connected", False):
                return False
            return True
        except Exception as e:
            logger.error(f"Failed to check setup status: {str(e)}")
            return True


class SetupStatusChecker:
    """
    Utility class for checking setup status.
    
    This can be used by other parts of the application to check setup status.
    """
    
    @staticmethod
    async def is_setup_required() -> bool:
        """Check if setup is required."""
        try:
            setup_status = await get_setup_status_service().get_setup_status()
            return not setup_status.get("setup_complete", False)
        except Exception:
            return True
    
    @staticmethod
    async def mark_setup_completed() -> bool:
        """Mark setup as completed."""
        try:
            await redis_client.connect()
            await redis_client.set("setup:completed", "true", expire=86400 * 365)  # Expire in 1 year
            return True
        except Exception:
            return False
    
    @staticmethod
    async def reset_setup() -> bool:
        """Reset setup status (for testing/development)."""
        try:
            await redis_client.connect()
            await redis_client.delete("setup:completed")
            return True
        except Exception:
            return False
