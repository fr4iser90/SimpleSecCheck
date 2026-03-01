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
    cancel_shutdown,
    shutdown_now,
    toggle_auto_shutdown,
    get_shutdown_status,
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
    # OWASP Update service
    UpdateStatus,
    start_update as start_update_service,
    get_update_status as get_update_status_service,
    get_update_logs as get_update_logs_service,
    stop_update as stop_update_service,
)
from app.services.ai_prompt_service import collect_findings_from_results, generate_ai_prompt

# Configuration
# Try multiple paths for flexibility (dev vs production)
BASE_DIR = Path(__file__).parent.parent.parent.parent  # SimpleSecCheck root
if not (BASE_DIR / "bin" / "run-docker.sh").exists():
    # Try alternative path (when running in container)
    BASE_DIR = Path("/app")

CLI_SCRIPT = BASE_DIR / "bin" / "run-docker.sh"
RESULTS_DIR = BASE_DIR / "results"
LOGS_DIR = BASE_DIR / "logs"
OWASP_DATA_DIR = BASE_DIR / "owasp-dependency-check-data"

# CLI script is only needed for direct CLI usage (not for WebUI)
# WebUI calls docker-compose directly, so this validation is optional
if not CLI_SCRIPT.exists() and os.path.exists("/app"):
    # Running in container (WebUI) - script not needed
    pass
elif not CLI_SCRIPT.exists():
    # Running on host without script - warn but don't fail (WebUI doesn't need it)
    print(f"[WARNING] CLI script not found: {CLI_SCRIPT} (WebUI will use docker-compose directly)")

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


@app.get("/api/git/branches")
async def get_git_branches(url: str):
    """
    Get available branches from a Git repository.
    Uses git ls-remote to fetch branches without cloning.
    """
    update_activity()
    
    import subprocess
    import re
    from urllib.parse import urlparse
    
    # Validate URL
    if not url or not url.strip():
        raise HTTPException(status_code=400, detail="URL is required")
    
    git_url = url.strip()
    
    # Normalize Git URL (add .git if needed for HTTPS URLs)
    if not git_url.startswith("git@") and not git_url.endswith(".git") and not git_url.endswith("/"):
        git_url = git_url + ".git"
    
    try:
        # Use git ls-remote to fetch branches without cloning
        # This is fast and doesn't require authentication for public repos
        result = subprocess.run(
            ["git", "ls-remote", "--heads", git_url],
            capture_output=True,
            text=True,
            timeout=10,  # 10 second timeout
            check=False  # Don't raise on error, we'll handle it
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            
            # Provide user-friendly error messages
            if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
                raise HTTPException(
                    status_code=404,
                    detail=f"Repository not found: {url}. Please check the URL and ensure the repository exists and is accessible."
                )
            elif "permission denied" in error_msg.lower() or "authentication" in error_msg.lower():
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {url}. Private repositories require authentication. You can still manually enter a branch name."
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to fetch branches: {error_msg}. You can still manually enter a branch name."
                )
        
        # Parse branches from output
        # Format: <commit-hash>	refs/heads/<branch-name>
        branches = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                match = re.search(r'refs/heads/(.+)', line)
                if match:
                    branch_name = match.group(1)
                    branches.append(branch_name)
        
        # Sort branches (put common ones first)
        common_branches = ['main', 'master', 'develop', 'dev', 'staging', 'production', 'prod']
        sorted_branches = []
        seen = set()
        
        # Add common branches first if they exist
        for common in common_branches:
            if common in branches:
                sorted_branches.append(common)
                seen.add(common)
        
        # Add remaining branches
        for branch in sorted(branches):
            if branch not in seen:
                sorted_branches.append(branch)
        
        return {
            "branches": sorted_branches,
            "default": sorted_branches[0] if sorted_branches else None
        }
        
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=408,
            detail="Timeout while fetching branches. You can still manually enter a branch name."
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error while fetching branches: {str(e)}. You can still manually enter a branch name."
        )


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
        RESULTS_DIR
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
    
    # Find steps.log file - MUST match current scan_id to avoid reading old scans
    steps_log = None
    scan_id = current_scan.get("scan_id")
    
    if not scan_id:
        return {"lines": [], "count": 0}
    
    # First try: Use results_dir if set and matches scan_id
    if current_scan.get("results_dir"):
        results_dir_path = current_scan["results_dir"]
        if scan_id in results_dir_path:
            steps_log = Path(results_dir_path) / "logs" / "steps.log"
    
    # Second try: Find by scan_id (MUST match exactly)
    if not steps_log and RESULTS_DIR.exists():
        for scan_dir in sorted(RESULTS_DIR.iterdir(), reverse=True):
            if scan_dir.is_dir() and scan_id in scan_dir.name:
                # CRITICAL: Verify this is really the current scan
                # Check if scan_id is in directory name (could be scan_scan_id or PROJECT_NAME_scan_id)
                steps_log = scan_dir / "logs" / "steps.log"
                break
    
    # Read and return all lines - ONLY if file exists and belongs to current scan
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


@app.get("/api/scan/ai-prompt")
async def get_ai_prompt(
    token_saving: bool = False,
    language: str = "english",
    policy_path: str = "config/finding-policy.json"
):
    """
    Generate AI prompt with all findings for false positive analysis
    
    Args:
        token_saving: If True, generate Chinese prompt (token-efficient) - DEPRECATED, use language instead
        language: Language for prompt (english, chinese, german)
        policy_path: Path where finding policy should be placed
    """
    update_activity()
    
    if current_scan["results_dir"] is None:
        raise HTTPException(status_code=404, detail="No scan results available")
    
    results_dir = Path(current_scan["results_dir"])
    
    # Collect all findings
    findings = collect_findings_from_results(results_dir)
    
    if not findings:
        raise HTTPException(status_code=404, detail="No findings found in scan results")
    
    # Normalize language (backward compatibility: token_saving=True means chinese)
    if token_saving:
        language = "chinese"
    language = language.lower()
    if language not in ["english", "chinese", "german"]:
        language = "english"
    
    # Generate prompt
    prompt = generate_ai_prompt(findings, language=language, policy_path=policy_path)
    
    return {
        "prompt": prompt,
        "findings_count": len(findings),
        "language": language,
        "policy_path": policy_path
    }


@app.get("/api/shutdown/status")
async def get_shutdown_status_endpoint():
    """Get current shutdown status"""
    update_activity()
    return get_shutdown_status(current_scan)


@app.post("/api/shutdown/toggle")
async def toggle_shutdown(request: dict):
    """Toggle auto-shutdown on/off"""
    update_activity()
    enabled = request.get("enabled", True)
    toggle_auto_shutdown(enabled)
    return {
        "auto_shutdown_enabled": AUTO_SHUTDOWN_ENABLED,
        "message": f"Auto-shutdown {'enabled' if AUTO_SHUTDOWN_ENABLED else 'disabled'}"
    }


@app.post("/api/shutdown/now")
async def shutdown_now_endpoint():
    """Shutdown immediately"""
    update_activity()
    shutdown_now()
    return {"message": "Shutting down now..."}


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


@app.post("/api/owasp/update", response_model=UpdateStatus)
async def start_owasp_update():
    """Start OWASP Dependency Check database update"""
    update_activity()
    
    result = await start_update_service(
        BASE_DIR,
        OWASP_DATA_DIR,
    )
    
    return result


@app.get("/api/owasp/status", response_model=UpdateStatus)
async def get_owasp_update_status():
    """Get current OWASP update status"""
    update_activity()
    return get_update_status_service()


@app.get("/api/owasp/logs")
async def get_owasp_update_logs():
    """Get logs from current OWASP update (simple polling endpoint)"""
    update_activity()
    return get_update_logs_service()


@app.post("/api/owasp/stop", response_model=UpdateStatus)
async def stop_owasp_update():
    """Stop the currently running OWASP update"""
    update_activity()
    return stop_update_service()


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
    # Security: Default to localhost, allow override via environment variable for Docker
    # In Docker containers, set HOST=0.0.0.0 to allow external access
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host=host, port=port)
