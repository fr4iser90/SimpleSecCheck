"""
Bulk Scan Routes
"""
from fastapi import APIRouter, HTTPException
from app.services import update_activity
from app.services.batch_scan_service import (
    BatchScanRequest,
    BatchScanProgress,
    start_batch_scan,
    get_batch_scan_progress,
    pause_batch_scan,
    resume_batch_scan,
    stop_batch_scan,
)

router = APIRouter()

# Will be injected from main
BASE_DIR = None
RESULTS_DIR = None
CLI_SCRIPT = None


def init_bulk_router(base_dir, results_dir, cli_script):
    """Initialize router with directories"""
    global BASE_DIR, RESULTS_DIR, CLI_SCRIPT
    BASE_DIR = base_dir
    RESULTS_DIR = results_dir
    CLI_SCRIPT = cli_script


@router.post("/api/bulk/start", response_model=BatchScanProgress)
async def start_bulk_scan_route(request: BatchScanRequest):
    """Start a batch scan for multiple repositories"""
    update_activity()
    return await start_batch_scan(request, BASE_DIR, RESULTS_DIR, CLI_SCRIPT)


@router.get("/api/bulk/status", response_model=BatchScanProgress)
async def get_bulk_scan_status(batch_id: str = None):
    """Get status of current batch scan"""
    update_activity()
    progress = get_batch_scan_progress(batch_id)
    if not progress:
        raise HTTPException(status_code=404, detail="No batch scan found")
    return progress


@router.post("/api/bulk/pause")
async def pause_bulk_scan_route():
    """Pause the current batch scan"""
    update_activity()
    await pause_batch_scan()
    progress = get_batch_scan_progress()
    if not progress:
        raise HTTPException(status_code=404, detail="No batch scan found")
    return progress


@router.post("/api/bulk/resume")
async def resume_bulk_scan_route():
    """Resume a paused batch scan"""
    update_activity()
    await resume_batch_scan()
    progress = get_batch_scan_progress()
    if not progress:
        raise HTTPException(status_code=404, detail="No batch scan found")
    return progress


@router.post("/api/bulk/stop")
async def stop_bulk_scan_route():
    """Stop the current batch scan"""
    update_activity()
    await stop_batch_scan()
    progress = get_batch_scan_progress()
    if not progress:
        raise HTTPException(status_code=404, detail="No batch scan found")
    return progress
