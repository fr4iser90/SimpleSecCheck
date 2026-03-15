"""
FastAPI Application Main Module

This module sets up the FastAPI application with all routes, middleware, and dependencies.
Implements the complete API layer with authentication, validation, and logging.
"""
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import time

from api.routes import scans, auth, setup, scanners, admin, queue, git
from api import health as health_module
from api.middleware.auth_middleware import (
    AuthMiddleware, SecurityHeadersMiddleware
)
from api.middleware.logging_middleware import LoggingMiddleware
from api.middleware.setup_middleware import SetupMiddleware
from api.deps.actor_context import ActorContextDependency
from prometheus_fastapi_instrumentator import Instrumentator
from config.settings import settings
from infrastructure.logging_config import setup_logging

# Import test container for testing
import os
if os.environ.get("ENVIRONMENT") == "test":
    from tests.unit.test_container import get_test_scan_service


# Set up logging
setup_logging()

# Create logger (will be replaced in functions with structlog)
from infrastructure.logging_config import get_logger
logger = get_logger("api.main")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="SimpleSecCheck API",
        description="Security scanning API with DDD architecture",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        debug=True
    )
    
    # Instrument the app for metrics FIRST (before adding custom middleware)
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics"],
    )
    
    instrumentator.instrument(app).expose(app, endpoint="/metrics")
    
    # Initialize actor context dependency
    actor_context_dependency = ActorContextDependency(
        jwt_secret_key=settings.jwt_secret_key,
        jwt_algorithm=settings.jwt_algorithm,
        jwt_expiration_minutes=settings.jwt_expiration_minutes,
        environment=settings.SECURITY_MODE,
    )
    
    # Configure middleware stack in correct order
    # 1. Trusted Host (security)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]
    )
    
    # 2. CORS (security)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # 3. Logging (observability)
    app.add_middleware(LoggingMiddleware)
    
    # 4. Security Headers (security)
    app.add_middleware(SecurityHeadersMiddleware, environment=settings.SECURITY_MODE)
    
    # 5. Setup (security)
    app.add_middleware(SetupMiddleware, environment=settings.SECURITY_MODE)
    
    # 6. Auth (security)
    # Configure protected paths based on authentication mode
    if settings.AUTH_MODE == "free":
        # FREE mode: Only admin paths require authentication
        protected_paths = []
    else:
        # BASIC/JWT modes: Scans and other features require authentication
        protected_paths = [
            "/api/v1/scans",
            "/api/v1/queue",
            "/api/v1/stats",
        ]
    
    app.add_middleware(
        AuthMiddleware,
        actor_context_dependency=actor_context_dependency,
        protected_paths=protected_paths,
        public_paths=[
            "/api/v1/health",
            "/api/v1/auth/login",
            "/api/v1/auth/guest",
            "/api/v1/auth/session",
            "/api/v1/auth/refresh",
            "/api/v1/auth/me",
            "/api/v1/auth/admin/users",
            "/api/v1/auth/logout",
            "/api/setup",
            "/api/setup/status",
            "/api/setup/health",
            "/api/setup/initialize",
            "/api/setup/skip",
        ],
        admin_paths=[
            "/api/v1/auth/admin",
        ],
        environment=settings.SECURITY_MODE,
    )
        
    
    app.include_router(scans.router)
    app.include_router(auth.router)
    app.include_router(setup.router)
    app.include_router(scanners.router)
    app.include_router(scanners.config_router)
    app.include_router(admin.router)
    app.include_router(queue.router)
    app.include_router(git.router)
    app.include_router(health_module.router)
    app.include_router(health_module.shutdown_router)
    
    # Add global exception handlers
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(Exception, handle_general_exception)
    
    # Add startup and shutdown events
    app.add_event_handler("startup", startup_event)
    app.add_event_handler("shutdown", shutdown_event)
    
    return app


async def handle_validation_error(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    from infrastructure.logging_config import get_logger
    logger = get_logger("api.main")
    logger.warning(
        "Validation error",
        method=request.method,
        path=request.url.path,
        errors=exc.errors(),
    )
    
    # Return simple response to avoid Content-Length conflicts
    return PlainTextResponse(content="Validation failed", status_code=400)


async def handle_http_exception(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    from infrastructure.logging_config import get_logger
    logger = get_logger("api.main")
    
    # Suppress 404 logs for known frontend polling endpoints
    if exc.status_code == 404 and request.url.path in ["/api/shutdown/status", "/api/scan/status"]:
        # Don't log these - they're just frontend polling endpoints that may not exist
        pass
    else:
        logger.info(
            "HTTP exception",
            status_code=exc.status_code,
            message=exc.detail,
            method=request.method,
            path=request.url.path,
        )
    
    # Return simple response to avoid Content-Length conflicts
    return PlainTextResponse(content=exc.detail, status_code=exc.status_code)


async def handle_general_exception(request: Request, exc: Exception):
    """Handle general exceptions."""
    from infrastructure.logging_config import get_logger
    logger = get_logger("api.main")
    logger.error(
        "General exception",
        error_type=type(exc).__name__,
        error_message=str(exc),
        method=request.method,
        path=request.url.path,
        exc_info=True,
    )
    
    # Return simple response to avoid Content-Length conflicts
    return PlainTextResponse(content="Internal server error", status_code=500)


async def startup_event():
    """Handle application startup."""
    from infrastructure.logging_config import get_logger
    logger = get_logger("api.main")
    
    # Initialize database connection
    try:
        from infrastructure.database.adapter import db_adapter
        await db_adapter.init_database()
        logger.info("Database connected")
        
        # Create tables if they don't exist
        try:
            tables_exist = await db_adapter.check_tables_exist()
            if not all(tables_exist.values()):
                await db_adapter.create_tables()
            else:
                # Tables exist, but run migrations for schema updates
                await db_adapter._migrate_existing_tables()
        except Exception as e:
            # If table creation fails, log but don't fail startup
            logger.error("Failed to create database tables", error=str(e))
        
        # Load settings from database if setup is completed
        try:
            from config.settings import load_settings_from_database, settings
            await load_settings_from_database(settings)
            logger.info("Settings loaded from database (if setup completed)")
        except Exception as e:
            logger.debug("Could not load settings from database (setup may not be completed)", error=str(e))
            
    except Exception as e:
        logger.error("Database connection failed", error=str(e))
    
    logger.info("API started")
    
    # Generate setup token only if setup is not complete
    try:
        from api.services.setup_token_service import SetupTokenService
        from infrastructure.database.models import SystemState, SetupStatusEnum
        from sqlalchemy import select
        from datetime import datetime
        
        # Check if system is already set up
        setup_required = True
        try:
            # Check if system_state table exists
            table_exists = await db_adapter.check_table_exists("system_state")
            logger.info(f"[DEBUG startup_event] system_state table exists: {table_exists}")
            
            if table_exists:
                session = await db_adapter.get_session()
                async with session:
                    result = await session.execute(select(SystemState).limit(1))
                    system_state = result.scalar_one_or_none()
                    
                    logger.info(f"[DEBUG startup_event] system_state found: {system_state is not None}")
                    
                    if system_state:
                        # Check if setup is complete - must have all flags set
                        setup_complete = (
                            (system_state.setup_status == SetupStatusEnum.COMPLETED or
                             system_state.setup_status == SetupStatusEnum.LOCKED) and
                            system_state.setup_locked and
                            system_state.database_initialized and
                            system_state.admin_user_created and
                            system_state.system_configured
                        )
                        
                        logger.info(
                            f"[DEBUG startup_event] Setup check: status={system_state.setup_status.value}, "
                            f"locked={system_state.setup_locked}, "
                            f"db_init={system_state.database_initialized}, "
                            f"admin_created={system_state.admin_user_created}, "
                            f"sys_configured={system_state.system_configured}, "
                            f"setup_complete={setup_complete}"
                        )
                        
                        if setup_complete:
                            setup_required = False
                            logger.info("System setup already complete, skipping token generation")
                    else:
                        logger.info("[DEBUG startup_event] No system_state record found, setup required")
            else:
                logger.info("[DEBUG startup_event] system_state table does not exist, setup required")
        except Exception as e:
            # If we can't check, assume setup is required (safer)
            logger.warning(f"Could not check setup status, assuming setup required: {e}", exc_info=True)
        
        # Only generate token if setup is required
        if setup_required:
            token_service = SetupTokenService()
            token = token_service.generate_token()
            token_hash = token_service.hash_token(token)
            created_at = datetime.utcnow()
            print(f"[DEBUG startup_event] Generated token: hash[:16]={token_hash[:16]}..., created_at={created_at}")
            
            # Store token in database - retry if table was just created
            token_stored = False
            max_retries = 5
            for attempt in range(max_retries):
                print(f"[DEBUG startup_event] Attempt {attempt + 1}/{max_retries} to store token in DB")
                token_stored = await token_service.store_setup_token(token_hash, created_at)
                print(f"[DEBUG startup_event] store_setup_token returned: {token_stored}")
                if token_stored:
                    break
                # If tables were just created, wait a bit and retry
                if attempt < max_retries - 1:
                    import asyncio
                    print(f"[DEBUG startup_event] Tables were just created, waiting 1s before retry...")
                    await asyncio.sleep(1)
            
            # Log token to stdout (not central logs) - always log even if storage failed
            token_service.log_token_generation(token)
            
            if token_stored:
                logger.info("Setup token generated and stored")
            else:
                logger.warning("Setup token generated but not stored (tables may not exist yet)")
        
    except Exception as e:
        logger.error("Failed to generate setup token", error=str(e))
    
    # Re-enqueue pending scans that may have been lost from queue
    try:
        await _re_enqueue_pending_scans()
    except Exception as e:
        logger.error("Failed to re-enqueue pending scans", error=str(e), exc_info=True)


async def _re_enqueue_pending_scans():
    """Re-enqueue all pending scans and recover running scans that may have been lost from the queue."""
    from infrastructure.logging_config import get_logger
    logger = get_logger("api.main")
    
    try:
        from infrastructure.repositories.scan_repository import DatabaseScanRepository
        from infrastructure.services.queue_service import QueueService
        from domain.entities.scan import ScanStatus
        from infrastructure.database.adapter import db_adapter
        from sqlalchemy import select, update
        from infrastructure.database.models import Scan as ScanModel
        from datetime import datetime
        
        # Get repository and queue service
        scan_repository = DatabaseScanRepository()
        queue_service = QueueService()
        
        # Get all pending scans
        pending_scans = await scan_repository.get_by_status(ScanStatus.PENDING, limit=1000)
        
        # Get all running scans (these were likely interrupted by restart)
        running_scans = await scan_repository.get_by_status(ScanStatus.RUNNING, limit=1000)
        
        total_scans = len(pending_scans) + len(running_scans)
        
        if total_scans == 0:
            logger.info("No pending or running scans to re-enqueue")
            return
        
        logger.info(f"Found {len(pending_scans)} pending scans and {len(running_scans)} running scans to recover")
        
        # Reset running scans to pending (they were interrupted by restart)
        recovered_scans = []
        if running_scans:
            await db_adapter.ensure_initialized()
            async with db_adapter.async_session() as session:
                for scan in running_scans:
                    try:
                        from uuid import UUID
                        scan_uuid = UUID(scan.id)
                        
                        # Reset status to pending and clear started_at
                        update_stmt = (
                            update(ScanModel)
                            .where(ScanModel.id == scan_uuid)
                            .values(
                                status="pending",
                                started_at=None,
                                updated_at=datetime.utcnow(),
                                error_message=None
                            )
                        )
                        await session.execute(update_stmt)
                        
                        # Reload scan entity to get updated status
                        reloaded_scan = await scan_repository.get_by_id(scan.id)
                        if reloaded_scan:
                            recovered_scans.append(reloaded_scan)
                            logger.info(f"Reset running scan {scan.id} to pending (was interrupted by restart)")
                    except Exception as e:
                        logger.error(f"Failed to reset running scan {scan.id}: {e}", exc_info=True)
                
                await session.commit()
        
        # Combine all scans to re-enqueue (pending + recovered running scans)
        all_scans = list(pending_scans) + recovered_scans
        
        # Re-enqueue each scan
        enqueued_count = 0
        failed_count = 0
        
        for scan in all_scans:
            try:
                await queue_service.enqueue_scan(scan)
                enqueued_count += 1
                logger.debug(f"Re-enqueued scan {scan.id}")
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to re-enqueue scan {scan.id}: {e}", exc_info=True)
        
        logger.info(
            f"Re-enqueue complete: {enqueued_count} successful, {failed_count} failed out of {total_scans} total "
            f"({len(pending_scans)} pending + {len(running_scans)} recovered running)"
        )
        
    except Exception as e:
        logger.error(f"Error during re-enqueue of pending scans: {e}", exc_info=True)
        # Don't raise - we don't want to fail startup if this fails


async def shutdown_event():
    """Handle application shutdown."""
    logger.info(
        "SimpleSecCheck API shutting down",
        extra={"structured_data": {
            "event": "shutdown",
            "timestamp": time.time(),
        }}
    )
    
    # Clean up services here
    # For example: close database connections, Redis connections, etc.
    
    logger.info("SimpleSecCheck API shutdown complete")


# Create the application instance
app = create_app()


@app.get("/api/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}




@app.get("/api/info", tags=["info"])
async def api_info():
    """API information endpoint."""
    return {
        "name": "SimpleSecCheck API",
        "version": "1.0.0",
        "description": "Security scanning API with DDD architecture",
        "features": [
            "Authentication & Authorization",
            "Scan Management",
            "Result Processing",
            "Queue Management",
            "Statistics & Reporting",
            "Guest & Authenticated Users",
        ],
        "documentation": "/api/docs",
        "openapi": "/api/openapi.json",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info",
    )
