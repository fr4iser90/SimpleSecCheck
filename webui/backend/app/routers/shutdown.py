"""
Shutdown Routes
"""
from fastapi import APIRouter
from app.services import (
    update_activity,
    get_shutdown_status,
    toggle_auto_shutdown,
    shutdown_now,
    AUTO_SHUTDOWN_ENABLED,
)

router = APIRouter()

# Will be injected from main
current_scan = None


def init_shutdown_router(scan_state: dict):
    """Initialize router with scan state"""
    global current_scan
    current_scan = scan_state


@router.get("/api/shutdown/status")
async def get_shutdown_status_endpoint():
    """Get current shutdown status"""
    update_activity()
    return get_shutdown_status(current_scan)


@router.post("/api/shutdown/toggle")
async def toggle_shutdown(request: dict):
    """Toggle auto-shutdown on/off"""
    update_activity()
    enabled = request.get("enabled", True)
    toggle_auto_shutdown(enabled)
    return {
        "auto_shutdown_enabled": AUTO_SHUTDOWN_ENABLED,
        "message": f"Auto-shutdown {'enabled' if AUTO_SHUTDOWN_ENABLED else 'disabled'}"
    }


@router.post("/api/shutdown/now")
async def shutdown_now_endpoint():
    """Shutdown immediately"""
    update_activity()
    shutdown_now()
    return {"message": "Shutting down now..."}
