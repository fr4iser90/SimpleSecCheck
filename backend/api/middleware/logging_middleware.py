"""
Logging Middleware

This module provides middleware for structured logging of API requests and responses.
Includes request tracking, performance monitoring, and error logging.
"""
import time
import json
import structlog
from typing import Callable, Awaitable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message
import logging

from api.deps.actor_context import ActorContext


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Structured logging middleware for API requests and responses.
    
    This middleware:
    - Logs all incoming requests with context
    - Logs response status and timing
    - Tracks request duration
    - Logs errors and exceptions
    - Provides request correlation IDs
    """
    
    def __init__(self, app, logger_name: str = "api"):
        """
        Initialize logging middleware.
        
        Args:
            app: FastAPI application instance
            logger_name: Name for the logger
        """
        super().__init__(app)
        self.logger_name = logger_name
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process incoming request and log details.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response
        """
        # Skip logging for health checks and static files
        skip_paths = ["/api/health", "/metrics", "/static", "/docs", "/openapi.json"]
        if request.url.path in skip_paths:
            return await call_next(request)
        
        # Generate correlation ID
        correlation_id = self._generate_correlation_id()
        request.state.correlation_id = correlation_id
        
        # Get actor context
        actor_context = getattr(request.state, 'actor_context', None)
        
        # Bind trace ID for structlog context (with proper cleanup)
        from structlog.contextvars import bind_contextvars, clear_contextvars
        bind_contextvars(trace_id=correlation_id)
        
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Log request completion (only errors or slow requests)
            duration = time.time() - start_time
            if response.status_code >= 400 or duration > 1.0:
                await self._log_request_completion(
                    request, response, correlation_id, duration, actor_context
                )
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            
            return response
            
        except Exception as e:
            # Log request error
            duration = time.time() - start_time
            await self._log_request_error(
                request, e, correlation_id, duration, actor_context
            )
            
            # Re-raise the exception
            raise
        finally:
            # Always clear context to prevent leaks
            clear_contextvars()
    
    def _generate_correlation_id(self) -> str:
        """Generate a unique correlation ID for request tracking."""
        import uuid
        return str(uuid.uuid4())
    
    async def _log_request_start(
        self,
        request: Request,
        correlation_id: str,
        actor_context: ActorContext
    ) -> None:
        """Log the start of a request (not used anymore, kept for compatibility)."""
        # Request start logging removed to reduce log spam
        pass
    
    async def _log_request_completion(
        self,
        request: Request,
        response: Response,
        correlation_id: str,
        duration: float,
        actor_context: ActorContext
    ) -> None:
        """Log the completion of a request (only errors or slow requests)."""
        # Only log errors or slow requests
        if response.status_code >= 400:
            logger = structlog.get_logger("api.middleware")
            logger.warning(
                "Request completed with error",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
            )
    
    async def _log_request_error(
        self,
        request: Request,
        error: Exception,
        correlation_id: str,
        duration: float,
        actor_context: ActorContext
    ) -> None:
        """Log request errors and exceptions."""
        logger = structlog.get_logger(self.logger_name)
        logger.error(
            "Request failed",
            method=request.method,
            path=request.url.path,
            error_type=type(error).__name__,
            error_message=str(error),
            duration_ms=round(duration * 1000, 2),
            exc_info=True,
        )
    
    def _sanitize_headers(self, headers: dict) -> dict:
        """Sanitize headers to remove sensitive information."""
        sanitized = {}
        sensitive_headers = {
            "authorization", "x-api-key", "cookie", "x-auth-token",
            "x-session-token", "x-csrf-token"
        }
        
        for key, value in headers.items():
            if key.lower() in sensitive_headers:
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _get_client_ip(self, request: Request) -> str:
        """Get the client IP address from request headers."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct connection
        if request.client:
            return request.client.host
        
        return "unknown"


class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    Performance monitoring middleware.
    
    This middleware:
    - Tracks request duration
    - Identifies slow requests
    - Monitors resource usage
    - Provides performance metrics
    """
    
    def __init__(
        self,
        app,
        slow_request_threshold: float = 1.0,  # 1 second
        logger_name: str = "performance"
    ):
        """
        Initialize performance middleware.
        
        Args:
            app: FastAPI application instance
            slow_request_threshold: Threshold for slow requests in seconds
            logger_name: Name for the performance logger
        """
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold
        self.logger = logging.getLogger(logger_name)
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process incoming request and monitor performance.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response
        """
        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.perf_counter() - start_time
            
            # Log performance metrics
            await self._log_performance_metrics(request, response, duration)
            
            return response
            
        except Exception:
            # Calculate duration even for failed requests
            duration = time.perf_counter() - start_time
            await self._log_performance_metrics(request, None, duration)
            raise
    
    async def _log_performance_metrics(
        self,
        request: Request,
        response: Response,
        duration: float
    ) -> None:
        """Log performance metrics for the request."""
        log_data = {
            "method": request.method,
            "path": request.url.path,
            "duration_seconds": round(duration, 4),
            "is_slow_request": duration > self.slow_request_threshold,
            "timestamp": time.time(),
        }
        
        if response:
            log_data["status_code"] = response.status_code
            log_data["content_length"] = response.headers.get("content-length", "unknown")
        
        # Log slow requests with warning level
        if duration > self.slow_request_threshold:
            self.logger.warning(
                f"Slow request detected: {request.method} {request.url.path} took {duration:.4f}s",
                extra={"structured_data": log_data}
            )
        else:
            self.logger.debug(
                f"Request completed: {request.method} {request.url.path} took {duration:.4f}s",
                extra={"structured_data": log_data}
            )


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """
    Request size monitoring middleware.
    
    This middleware:
    - Tracks request and response sizes
    - Logs large requests/responses
    - Helps identify potential performance issues
    """
    
    def __init__(
        self,
        app,
        max_request_size: int = 10 * 1024 * 1024,  # 10MB
        max_response_size: int = 50 * 1024 * 1024,  # 50MB
        logger_name: str = "request_size"
    ):
        """
        Initialize request size middleware.
        
        Args:
            app: FastAPI application instance
            max_request_size: Maximum allowed request size in bytes
            max_response_size: Maximum allowed response size in bytes
            logger_name: Name for the request size logger
        """
        super().__init__(app)
        self.max_request_size = max_request_size
        self.max_response_size = max_response_size
        self.logger = logging.getLogger(logger_name)
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process incoming request and monitor sizes.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response
        """
        # Get request size
        request_size = await self._get_request_size(request)
        
        # Check if request is too large
        if request_size > self.max_request_size:
            self.logger.warning(
                f"Large request detected: {request.method} {request.url.path} - {request_size} bytes",
                extra={"structured_data": {
                    "event": "large_request",
                    "method": request.method,
                    "path": request.url.path,
                    "size_bytes": request_size,
                    "max_size_bytes": self.max_request_size,
                    "timestamp": time.time(),
                }}
            )
        
        # Process request
        response = await call_next(request)
        
        # Get response size
        response_size = await self._get_response_size(response)
        
        # Check if response is too large
        if response_size > self.max_response_size:
            self.logger.warning(
                f"Large response detected: {request.method} {request.url.path} - {response_size} bytes",
                extra={"structured_data": {
                    "event": "large_response",
                    "method": request.method,
                    "path": request.url.path,
                    "size_bytes": response_size,
                    "max_size_bytes": self.max_response_size,
                    "timestamp": time.time(),
                }}
            )
        
        return response
    
    async def _get_request_size(self, request: Request) -> int:
        """Get the size of the request body in bytes."""
        try:
            # Read request body to get size
            body = await request.body()
            return len(body)
        except Exception:
            return 0
    
    async def _get_response_size(self, response: Response) -> int:
        """Get the size of the response body in bytes."""
        try:
            # Get content length from headers if available
            content_length = response.headers.get("content-length")
            if content_length:
                return int(content_length)
            
            # For streaming responses, we can't easily get the size
            # This is a limitation of the current implementation
            return 0
        except Exception:
            return 0