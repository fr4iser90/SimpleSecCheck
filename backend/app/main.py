#!/usr/bin/env python3
"""
SimpleSecCheck Backend
Minimal FastAPI backend that wraps the Python DockerRunner
Single-shot principle: No database, no state, just CLI wrapper
"""

import os
import asyncio
import threading
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

# Import services
from app.services import (
    # Shutdown service
    idle_timeout_checker,
    create_signal_handler,
    register_signal_handlers,
    AUTO_SHUTDOWN_ENABLED,
    IDLE_TIMEOUT,
    # Container service
    stop_running_containers,
)
from app.services.session_service import (
    session_middleware,
    get_session_service,
)
from app.services.queue_service import (
    get_queue_service,
)
from app.services.scanner_worker import (
    start_scanner_worker,
    stop_scanner_worker,
)
from app.services.scanner_asset_update_service import (
    start_asset_update as start_scanner_asset_update,
    get_asset_update_status as get_scanner_asset_update_status,
)

# Import routers
from app.routers import (
    health,
    scan,
    queue,
    session,
    results,
    shutdown,
    scanner_assets,
    github,
    bulk,
)

# Configuration - ALL PATHS FROM CENTRAL path_setup.py
# NO PATH CALCULATIONS HERE!
try:
    from core.path_setup import (
        get_backend_base_dir,
        get_backend_cli_script,
        get_backend_results_dir,
        get_backend_logs_dir,
        get_frontend_static_paths,
    )
    BASE_DIR = get_backend_base_dir()
    CLI_SCRIPT = get_backend_cli_script()
    RESULTS_DIR = get_backend_results_dir()
    LOGS_DIR = get_backend_logs_dir()
except Exception:
    BASE_DIR = Path("/app")
    CLI_SCRIPT = None
    RESULTS_DIR = BASE_DIR / "results"
    LOGS_DIR = BASE_DIR / "logs"

def get_frontend_static_paths() -> list[Path]:
    """Fallback frontend paths when scanner core isn't available."""
    return [BASE_DIR / "static", Path("/app/static")]

# CLI script is only needed for direct CLI usage (not for frontend)
# Frontend calls docker-compose directly, so this validation is optional
if CLI_SCRIPT and not CLI_SCRIPT.exists() and os.path.exists("/app"):
    # Running in container (backend) - script not needed
    pass
elif CLI_SCRIPT and not CLI_SCRIPT.exists():
    # Running on host without script - warn but don't fail (frontend doesn't need it)
    print(f"[WARNING] CLI script not found: {CLI_SCRIPT} (frontend will use docker-compose directly)")

app = FastAPI(title="SimpleSecCheck Backend", version="1.0.0")

# Environment detection
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev").lower()
IS_PRODUCTION = ENVIRONMENT == "prod"

# CORS configuration
cors_origins = os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if os.getenv("CORS_ALLOWED_ORIGINS") else []
cors_origins = [origin.strip() for origin in cors_origins if origin.strip()]
if not cors_origins:
    if IS_PRODUCTION:
        # In production, require explicit allowed origins
        cors_origins = []
    else:
        # Default to localhost for development
        cors_origins = ["http://localhost:8080", "http://127.0.0.1:8080"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware (only in production)
if IS_PRODUCTION:
    app.middleware("http")(session_middleware)
    print("[Main] Production mode: Session management enabled")
else:
    print("[Main] Development mode: Session management disabled")

# Global state for current scan (minimal, no DB)
current_scan = {
    "process": None,
    "status": "idle",  # idle, running, done, error
    "scan_id": None,
    "results_dir": None,
    "started_at": None,
    "error_code": None,
    "error_message": None,
    "process_output": [],  # Store process stdout/stderr lines for streaming
    "process_output_lock": threading.Lock(),  # Lock for thread-safe access
    "step_counter": 0,  # Step counter for frontend
    "step_names": {},  # Step names mapping
    "container_ids": [],  # Track running container IDs for cleanup
}

# Start idle timeout checker
if AUTO_SHUTDOWN_ENABLED and IDLE_TIMEOUT > 0:
    threading.Thread(target=idle_timeout_checker, args=(current_scan,), daemon=True).start()

# Register signal handlers
signal_handler = create_signal_handler(current_scan, stop_running_containers)
register_signal_handlers(signal_handler)

# Initialize services based on configuration
# Queue is ALWAYS enabled (works in both Dev and Prod, uses File-Database in Dev, PostgreSQL in Prod)
# Session Management is optional (enabled in Prod by default, can be enabled in Dev)
SESSION_MANAGEMENT = os.getenv("SESSION_MANAGEMENT", "true" if IS_PRODUCTION else "false").lower() == "true"
# Scanner worker can be disabled for frontend-only deployments
SCANNER_WORKER_ENABLED = os.getenv("SCANNER_WORKER_ENABLED", "true").lower() == "true"

async def queue_cleanup_task():
    """Background task for cleaning up old queue items"""
    from app.database import get_database
    
    cleanup_interval_hours = int(os.getenv("QUEUE_CLEANUP_INTERVAL_HOURS", "24"))
    max_age_days = int(os.getenv("QUEUE_CLEANUP_MAX_AGE_DAYS", "7"))
    
    print(f"[Queue Cleanup] Background task started (check every {cleanup_interval_hours}h, delete items older than {max_age_days} days)")
    
    while True:
        try:
            await asyncio.sleep(cleanup_interval_hours * 3600)  # Convert hours to seconds
            
            db = get_database()
            deleted_count = await db.cleanup_old_queue_items(max_age_days=max_age_days)
            
            if deleted_count > 0:
                print(f"[Queue Cleanup] Deleted {deleted_count} old queue items")
            else:
                print("[Queue Cleanup] No old queue items to clean up")
                
        except Exception as e:
            print(f"[Queue Cleanup] Error in background task: {e}")
            import traceback
            traceback.print_exc()
            # Wait before retrying
            await asyncio.sleep(3600)  # Wait 1 hour before retrying on error


async def scanner_assets_auto_update_task():
    """Background task for automatic scanner asset updates in production"""
    if os.getenv("SCANNER_PROXY_MODE", "false").lower() == "true":
        return
    auto_update_enabled = os.getenv("SCANNER_ASSETS_AUTO_UPDATE_ENABLED", "true" if IS_PRODUCTION else "false").lower() == "true"
    if not IS_PRODUCTION or not auto_update_enabled:
        return

    check_interval_hours = int(os.getenv("SCANNER_ASSETS_AUTO_UPDATE_CHECK_INTERVAL_HOURS", "24"))
    print(f"[Assets Auto-Update] Background task started (check every {check_interval_hours}h)")

    while True:
        try:
            await asyncio.sleep(check_interval_hours * 3600)
            status = get_scanner_asset_update_status()
            if status.status == "running":
                print("[Assets Auto-Update] Update already in progress, skipping check")
                continue

            # Example: auto-update OWASP data asset
            await start_scanner_asset_update("owasp", "data")
            print("[Assets Auto-Update] Triggered update for owasp:data")

        except Exception as e:
            print(f"[Assets Auto-Update] Error in background task: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(3600)


@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup"""
    try:
        # Initialize session service if enabled (needed by middleware)
        if SESSION_MANAGEMENT:
            session_service = await get_session_service()
            print("[Main] Session service initialized")
        
        # Initialize queue service (ALWAYS enabled - works in both Dev and Prod)
        queue_service = await get_queue_service()
        print("[Main] Queue service initialized")
        
        # Start scanner worker (optional; disable for frontend-only deployments)
        if SCANNER_WORKER_ENABLED:
            await start_scanner_worker()
            print("[Main] Scanner worker started")
        else:
            print("[Main] Scanner worker disabled (SCANNER_WORKER_ENABLED=false)")
        
        # Start queue cleanup background task (always enabled)
        asyncio.create_task(queue_cleanup_task())
        print("[Main] Queue cleanup background task started")
        
        # Start OWASP auto-update background task (only in production if enabled)
        if IS_PRODUCTION:
            asyncio.create_task(scanner_assets_auto_update_task())
            print("[Main] Assets auto-update background task started")
    except Exception as e:
        print(f"[Main] Failed to initialize services: {e}")
        import traceback
        traceback.print_exc()

@app.on_event("shutdown")
async def shutdown_event():
    """Stop services on application shutdown"""
    try:
        # Stop scanner worker (only if enabled)
        if SCANNER_WORKER_ENABLED:
            await stop_scanner_worker()
            print("[Main] Scanner worker stopped")
        
        # Close session service if enabled
        if SESSION_MANAGEMENT:
            session_service = await get_session_service()
            await session_service.close()
            print("[Main] Session service closed")
        
        # Close queue service (always enabled)
        queue_service = await get_queue_service()
        await queue_service.close()
        print("[Main] Queue service closed")
    except Exception as e:
        print(f"[Main] Error stopping services: {e}")


# Initialize routers with dependencies
health.init_health_router(ENVIRONMENT, IS_PRODUCTION)
scan.init_scan_router(IS_PRODUCTION, SESSION_MANAGEMENT, RESULTS_DIR, BASE_DIR, current_scan)
queue.init_queue_router(IS_PRODUCTION)
session.init_session_router(IS_PRODUCTION)
results.init_results_router(RESULTS_DIR)
shutdown.init_shutdown_router(current_scan)
github.init_github_router()
bulk.init_bulk_router(BASE_DIR, RESULTS_DIR, CLI_SCRIPT)

# Include routers
app.include_router(health.router)
app.include_router(scan.router)
app.include_router(queue.router)
app.include_router(session.router)
app.include_router(results.router)
app.include_router(shutdown.router)
app.include_router(scanner_assets.router)
app.include_router(github.router)
app.include_router(bulk.router)


# All routes moved to routers/ - see router imports above


# Serve frontend static files (after API routes)
# ALL PATHS FROM CENTRAL path_setup.py
frontend_paths = get_frontend_static_paths()

# Find frontend directory
frontend_dir = None
for fd in frontend_paths:
    if fd and fd.exists():
        frontend_dir = fd
        break

if frontend_dir:
    # Mount static assets (JS, CSS, images) - explicit path
    static_files = StaticFiles(directory=str(frontend_dir / "assets"), packages=None)
    app.mount("/assets", static_files, name="assets")
    
    # Catch-all handler for SPA routing: serve index.html for all non-API routes
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str, request: Request):
        """
        Catch-all handler for SPA routing.
        Serves index.html for all routes that don't match API endpoints.
        API routes are checked FIRST (defined before this handler), then this fallback.
        """
        # Don't serve index.html for API routes (should never reach here)
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        
        # Don't serve index.html for assets (already handled by /assets mount)
        if full_path.startswith("assets/"):
            raise HTTPException(status_code=404, detail="Not Found")
        
        # Serve index.html for all other routes (SPA routing)
        index_file = frontend_dir / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file), media_type="text/html")
        else:
            raise HTTPException(status_code=404, detail="Frontend not found")


if __name__ == "__main__":
    import uvicorn
    # Security: Default to localhost, allow override via environment variable for Docker
    # In Docker containers, set HOST=0.0.0.0 to allow external access
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host=host, port=port)
