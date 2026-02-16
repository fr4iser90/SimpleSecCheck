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
    # Message queue
    log_queue,
    active_websockets,
    log_worker_running,
    log_worker_thread,
    # Scan service
    ScanRequest,
    ScanStatus,
    start_scan as start_scan_service,
    get_scan_status as get_scan_status_service,
    stop_scan as stop_scan_service,
    # Log worker
    log_worker_thread_func,
    # WebSocket service
    websocket_logs as websocket_logs_service,
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
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
    
    # Stop previous log worker if running
    global log_worker_thread
    if log_worker_thread and log_worker_thread.is_alive():
        import app.services.message_queue as mq
        mq.log_worker_running = False
        log_worker_thread.join(timeout=1)
    
    result = await start_scan_service(
        request,
        current_scan,
        CLI_SCRIPT,
        BASE_DIR,
        RESULTS_DIR,
        log_worker_thread_func
    )
    
    # Update log_worker_thread from the service module
    import app.services.message_queue as mq
    log_worker_thread = mq.log_worker_thread
    
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


@app.websocket("/api/scan/logs/ws")
async def websocket_logs(websocket):
    """
    WebSocket endpoint for streaming logs.
    Uses message queue - separate worker thread reads steps.log and puts logs into queue.
    """
    await websocket_logs_service(websocket)


@app.get("/api/scan/logs")
async def stream_logs():
    """
    Stream logs from current scan (Server-Sent Events)
    Reads from results/*/logs/security-check.log
    Waits for log file to be created if scan just started
    """
    update_activity()
    
    print(f"[Log Stream Endpoint] Called: status={current_scan.get('status')}, scan_id={current_scan.get('scan_id')}, results_dir={current_scan.get('results_dir')}")
    print(f"[Log Stream Endpoint] Creating StreamingResponse...")
    
    async def generate():
        """Stream logs: first process output, then log file when available"""
        try:
            print(f"[Log Stream] Starting log stream for scan_id={current_scan.get('scan_id')}, status={current_scan.get('status')}")
            
            # Send initial message immediately
            initial_msg = json.dumps({'line': ' Starting security scan...'})
            print(f"[Log Stream] Sending initial message: {initial_msg}")
            yield f"data: {initial_msg}\n\n"
            print(f"[Log Stream] Initial message sent successfully")
        except Exception as e:
            print(f"[Log Stream] CRITICAL ERROR in generate() startup: {e}")
            import traceback
            traceback.print_exc()
            error_msg = json.dumps({'line': f'[ERROR] Failed to start log stream: {str(e)}'})
            yield f"data: {error_msg}\n\n"
            return
        
        # Try to find and stream steps.log file (written directly by security-check.sh)
        # steps.log is created immediately, so search actively for up to 3 seconds
        steps_log = None
        search_start = time.time()
        max_search_time = 3  # Wait up to 3 seconds for steps.log to appear
        
        while (time.time() - search_start) < max_search_time:
            # Try to find steps.log
            if current_scan.get("results_dir"):
                steps_log = Path(current_scan["results_dir"]) / "logs" / "steps.log"
            elif current_scan.get("scan_id") and RESULTS_DIR.exists():
                for scan_dir in sorted(RESULTS_DIR.iterdir(), reverse=True):
                    if scan_dir.is_dir() and current_scan["scan_id"] in scan_dir.name:
                        steps_log = scan_dir / "logs" / "steps.log"
                        current_scan["results_dir"] = str(scan_dir)
                        break
            
            # If found and exists, break and stream it
            if steps_log and steps_log.exists():
                print(f"[Log Stream] Found steps.log: {steps_log}")
                break
            
            # Wait a bit before checking again
            await asyncio.sleep(0.1)
        
        # Stream steps.log if it exists - CONTINUOUSLY TAIL IT
        if steps_log and steps_log.exists():
            try:
                steps_sent = 0
                # Open file and continuously tail it
                with open(steps_log, "r", encoding="utf-8", errors="ignore") as f:
                    # Read existing content first
                    existing_steps = f.readlines()
                    for step_line in existing_steps:
                        if step_line.strip():
                            line_msg = json.dumps({'line': step_line.strip()})
                            yield f"data: {line_msg}\n\n"
                            steps_sent += 1
                    
                    # Now continuously tail the file - ALWAYS, not just when running
                    # This ensures we get updates in real-time during the scan
                    last_position = f.tell()
                    max_idle_time = 10  # Stop after 10 seconds of no updates if scan is done
                    last_update_time = time.time()
                    scan_was_running = current_scan["status"] == "running"
                    
                    while True:
                        # Check if file has grown
                        f.seek(0, 2)  # Seek to end
                        current_position = f.tell()
                        
                        if current_position > last_position:
                            # File has new content - stream it immediately
                            f.seek(last_position)
                            new_lines = []
                            for step_line in f:
                                if step_line.strip():
                                    new_lines.append(step_line.strip())
                            
                            # Send all new lines
                            for step_line in new_lines:
                                line_msg = json.dumps({'line': step_line})
                                yield f"data: {line_msg}\n\n"
                                steps_sent += 1
                            
                            last_position = f.tell()
                            last_update_time = time.time()
                            scan_was_running = current_scan["status"] == "running"
                        else:
                            # No new content
                            current_status = current_scan["status"]
                            
                            # If scan is done and we've waited long enough, stop
                            if current_status in ["done", "error"]:
                                if time.time() - last_update_time > max_idle_time:
                                    print(f"[Log Stream] Scan finished, no updates for {max_idle_time}s, stopping stream")
                                    break
                            # If scan was running but now it's done, wait a bit more for final updates
                            elif scan_was_running and current_status in ["done", "error"]:
                                # Give it a bit more time for final log entries
                                if time.time() - last_update_time > 5:
                                    print(f"[Log Stream] Scan just finished, waiting for final updates...")
                                    break
                        
                        # Small sleep to avoid busy-waiting
                        await asyncio.sleep(0.1)
                        
            except Exception as e:
                print(f"[Log Stream] Error reading steps.log: {e}")
                import traceback
                traceback.print_exc()
                error_msg = json.dumps({'line': f'[ERROR] Failed to read steps.log: {str(e)}'})
                yield f"data: {error_msg}\n\n"
        else:
            # steps.log not found - continue searching for longer
            print(f"[Log Stream] steps.log not found after {max_search_time} seconds, continuing search...")
            extended_search_start = time.time()
            extended_max_search_time = 30  # Search for up to 30 seconds total
            
            while (time.time() - extended_search_start) < extended_max_search_time:
                # Try to find steps.log again
                if current_scan.get("results_dir"):
                    steps_log = Path(current_scan["results_dir"]) / "logs" / "steps.log"
                elif current_scan.get("scan_id") and RESULTS_DIR.exists():
                    for scan_dir in sorted(RESULTS_DIR.iterdir(), reverse=True):
                        if scan_dir.is_dir() and current_scan["scan_id"] in scan_dir.name:
                            steps_log = scan_dir / "logs" / "steps.log"
                            current_scan["results_dir"] = str(scan_dir)
                            break
                
                if steps_log and steps_log.exists():
                    print(f"[Log Stream] Found steps.log after extended search: {steps_log}")
                    # Now stream it continuously
                    try:
                        with open(steps_log, "r", encoding="utf-8", errors="ignore") as f:
                            # Read existing
                            for step_line in f:
                                if step_line.strip():
                                    line_msg = json.dumps({'line': step_line.strip()})
                                    yield f"data: {line_msg}\n\n"
                            
                            # Tail it continuously
                            last_position = f.tell()
                            last_update_time = time.time()
                            while True:
                                f.seek(0, 2)
                                current_position = f.tell()
                                if current_position > last_position:
                                    f.seek(last_position)
                                    for step_line in f:
                                        if step_line.strip():
                                            line_msg = json.dumps({'line': step_line.strip()})
                                            yield f"data: {line_msg}\n\n"
                                    last_position = f.tell()
                                    last_update_time = time.time()
                                elif current_scan["status"] in ["done", "error"]:
                                    if time.time() - last_update_time > 10:
                                        break
                                await asyncio.sleep(0.1)
                    except Exception as e:
                        print(f"[Log Stream] Error reading steps.log after extended search: {e}")
                        error_msg = json.dumps({'line': f'[ERROR] Failed to read steps.log: {str(e)}'})
                        yield f"data: {error_msg}\n\n"
                    break
                
                await asyncio.sleep(0.5)
            
            if not (steps_log and steps_log.exists()):
                error_msg = json.dumps({'line': f'[WARNING] steps.log not found after extended search. Scan may not have started yet.'})
                yield f"data: {error_msg}\n\n"
    
    print(f"[Log Stream Endpoint] Returning StreamingResponse...")
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Access-Control-Allow-Origin": "*",  # Allow CORS
            "Access-Control-Allow-Headers": "Cache-Control",
        }
    )


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
