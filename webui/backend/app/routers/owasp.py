"""
OWASP Dependency Check Routes
"""
from fastapi import APIRouter
from app.services import (
    update_activity,
    UpdateStatus,
    start_update as start_update_service,
    get_update_status as get_update_status_service,
    get_update_logs as get_update_logs_service,
    stop_update as stop_update_service,
)

router = APIRouter()

# Will be injected from main
BASE_DIR = None
OWASP_DATA_DIR = None


def init_owasp_router(base_dir, owasp_data_dir):
    """Initialize router with directories"""
    global BASE_DIR, OWASP_DATA_DIR
    BASE_DIR = base_dir
    OWASP_DATA_DIR = owasp_data_dir


@router.post("/api/owasp/update", response_model=UpdateStatus)
async def start_owasp_update():
    """Start OWASP Dependency Check database update"""
    update_activity()
    result = await start_update_service(BASE_DIR, OWASP_DATA_DIR)
    return result


@router.get("/api/owasp/status", response_model=UpdateStatus)
async def get_owasp_update_status():
    """Get current OWASP update status"""
    update_activity()
    return get_update_status_service(OWASP_DATA_DIR)


@router.get("/api/owasp/logs")
async def get_owasp_update_logs():
    """Get logs from current OWASP update (simple polling endpoint)"""
    update_activity()
    return get_update_logs_service()


@router.post("/api/owasp/stop", response_model=UpdateStatus)
async def stop_owasp_update():
    """Stop the currently running OWASP update"""
    update_activity()
    return stop_update_service()
