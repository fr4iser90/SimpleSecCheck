#!/usr/bin/env python3
"""
SimpleSecCheck WebUI Backend
Minimal FastAPI backend that wraps the CLI (bin/run-docker.sh)
Single-shot principle: No database, no state, just CLI wrapper
"""

import os
import asyncio
import threading
import json
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

# Import services
from app.services import (
    # Shutdown service
    update_activity,
    schedule_shutdown,
    idle_timeout_checker,
    create_signal_handler,
    register_signal_handlers,
    AUTO_SHUTDOWN_ENABLED,
    SHUTDOWN_AFTER_SCAN,
    SHUTDOWN_DELAY,
    IDLE_TIMEOUT,
    # Container service
    stop_running_containers,
    # Scan service
    ScanRequest,
    ScanStatus,
    start_scan as start_scan_service,
    get_scan_status as get_scan_status_service,
    stop_scan as stop_scan_service,
)

# Configuration
# Try multiple paths for flexibility (dev vs production)
BASE_DIR = Path(__file__).parent.parent.parent.parent  # SimpleSecCheck root
if not (BASE_DIR / "bin" / "run-docker.sh").exists():
    # Try alternative path (when running in container)
    BASE_DIR = Path("/app")

CLI_SCRIPT = BASE_DIR / "bin" / "run-docker.sh"
RESULTS_DIR = BASE_DIR / "results"
LOGS_DIR = BASE_DIR / "logs"

# Validate CLI script exists
if not CLI_SCRIPT.exists():
    raise RuntimeError(f"CLI script not found: {CLI_SCRIPT}")

app = FastAPI(title="SimpleSecCheck WebUI", version="1.0.0")

# CORS for development
# IMPORTANT: Cannot use allow_origins=["*"] with allow_credentials=True
# According to FastAPI docs: https://fastapi.tiangolo.com/tutorial/cors/
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],  # Explicit origins required when allow_credentials=True
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/api/health")
async def health():
    """Health check endpoint"""
    update_activity()
    return {"status": "ok", "service": "SimpleSecCheck WebUI"}


@app.post("/api/scan/start", response_model=ScanStatus)
async def start_scan(request: ScanRequest):
    """
    Start a scan by calling bin/run-docker.sh
    Single-shot: Only one scan at a time
    """
    update_activity()
    
    result = await start_scan_service(
        request,
        current_scan,
        CLI_SCRIPT,
        BASE_DIR,
        RESULTS_DIR,
        None  # log_worker_thread_func not needed anymore
    )
    
    return result


@app.get("/api/scan/status", response_model=ScanStatus)
async def get_scan_status():
    """Get current scan status"""
    update_activity()
    return await get_scan_status_service(current_scan, RESULTS_DIR)


@app.post("/api/scan/stop", response_model=ScanStatus)
async def stop_scan():
    """Stop the currently running scan"""
    update_activity()
    return await stop_scan_service(current_scan)


@app.get("/api/scan/logs")
async def get_logs():
    """
    Get logs from current scan (simple polling endpoint)
    Returns all lines from results/*/logs/steps.log
    """
    update_activity()
    
    # Find steps.log file
    steps_log = None
    if current_scan.get("results_dir"):
        steps_log = Path(current_scan["results_dir"]) / "logs" / "steps.log"
    elif current_scan.get("scan_id") and RESULTS_DIR.exists():
        for scan_dir in sorted(RESULTS_DIR.iterdir(), reverse=True):
            if scan_dir.is_dir() and current_scan["scan_id"] in scan_dir.name:
                steps_log = scan_dir / "logs" / "steps.log"
                break
    
    # Read and return all lines
    if steps_log and steps_log.exists():
        try:
            with open(steps_log, "r", encoding="utf-8", errors="ignore") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            return {"lines": lines, "count": len(lines)}
        except Exception as e:
            return {"lines": [], "count": 0, "error": str(e)}
    else:
        return {"lines": [], "count": 0}


@app.get("/api/scan/report")
async def get_report():
    """Get HTML report from current scan"""
    update_activity()
    
    if current_scan["results_dir"] is None:
        raise HTTPException(status_code=404, detail="No scan results available")
    
    report_file = Path(current_scan["results_dir"]) / "security-summary.html"
    
    if not report_file.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    
    return FileResponse(
        report_file,
        media_type="text/html",
        headers={"Content-Disposition": "inline"}
    )


@app.get("/api/results")
async def list_results():
    """
    List all scan results (file browser)
    No database - just reads results/ directory
    """
    update_activity()
    if not RESULTS_DIR.exists():
        return {"scans": []}
    
    scans = []
    for scan_dir in sorted(RESULTS_DIR.iterdir(), reverse=True):
        if scan_dir.is_dir():
            report_file = scan_dir / "security-summary.html"
            scans.append({
                "id": scan_dir.name,
                "timestamp": scan_dir.name,
                "has_report": report_file.exists(),
                "report_path": f"/api/results/{scan_dir.name}/report" if report_file.exists() else None
            })
    
    return {"scans": scans}


@app.get("/api/results/{scan_id}/report")
async def get_result_report(scan_id: str):
    """Get HTML report from specific scan"""
    report_file = RESULTS_DIR / scan_id / "security-summary.html"
    
    if not report_file.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    
    return FileResponse(
        report_file,
        media_type="text/html",
        headers={"Content-Disposition": "inline"}
    )


# Serve frontend static files (after API routes)
# Try multiple paths (dev vs production)
frontend_paths = [
    BASE_DIR / "webui" / "frontend" / "dist",
    BASE_DIR / "static",  # For docker-compose build
    Path("/app/static"),   # For docker container
]

for frontend_dir in frontend_paths:
    if frontend_dir.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="static")
        break


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
