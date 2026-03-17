"""
API Package

This package contains the FastAPI application and all API-related modules.
Includes routes, middleware, dependencies, and schemas for the API layer.
"""
from .main import app, create_app
from .deps.actor_context import (
    ActorContext,
    ActorContextDependency,
    get_actor_context,
    get_actor_context_dependency,
    get_authenticated_user,
    get_admin_user,
)
from .schemas.scan_schemas import (
    ScanRequestSchema,
    ScanResponseSchema,
    ScanSummarySchema,
    ScanUpdateSchema,
    ScanFilterSchema,
    ScanStatisticsSchema,
    CancelScanSchema,
    BatchScanSchema,
    ScanStatusResponseSchema,
    AggregatedResultSchema,
    VulnerabilitySchema,
    ScanResultSchema,
    ScanConfigSchema,
)
from .routes import scans, auth
# from .middleware import (
#     AuthMiddleware,
#     RateLimitMiddleware,
#     SecurityHeadersMiddleware,
#     LoggingMiddleware,
#     PerformanceMiddleware,
#     RequestSizeMiddleware,
#     InputValidationMiddleware,
#     OutputValidationMiddleware,
#     DataSanitizationMiddleware,
# )

__all__ = [
    # Application
    "app",
    "create_app",
    
    # Dependencies
    "ActorContext",
    "ActorContextDependency",
    "get_actor_context",
    "get_actor_context_dependency",
    "get_authenticated_user",
    "get_admin_user",
    
    # Schemas
    "ScanRequestSchema",
    "ScanResponseSchema",
    "ScanSummarySchema",
    "ScanUpdateSchema",
    "ScanFilterSchema",
    "ScanStatisticsSchema",
    "CancelScanSchema",
    "BatchScanSchema",
    "ScanStatusResponseSchema",
    "AggregatedResultSchema",
    "VulnerabilitySchema",
    "ScanResultSchema",
    "ScanConfigSchema",
    
    # Routes
    "scans",
    "auth",
    
    # Middleware
    "AuthMiddleware",
    "RateLimitMiddleware",
    "SecurityHeadersMiddleware",
    "LoggingMiddleware",
    "PerformanceMiddleware",
    "RequestSizeMiddleware",
    "InputValidationMiddleware",
    "OutputValidationMiddleware",
    "DataSanitizationMiddleware",
]