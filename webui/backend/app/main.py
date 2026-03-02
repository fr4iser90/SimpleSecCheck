#!/usr/bin/env python3
"""
SimpleSecCheck WebUI Backend
Minimal FastAPI backend that wraps the CLI (scripts/run-docker.sh)
Single-shot principle: No database, no state, just CLI wrapper
"""

import os
import asyncio
import threading
import json
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
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
from app.services.github_api_service import (
    list_user_repositories,
    list_org_repositories,
    get_rate_limit_info,
    validate_github_token,
    GitHubRepository,
    RateLimitInfo,
)
from app.services.batch_scan_service import (
    BatchScanRequest,
    BatchScanProgress,
    start_batch_scan,
    get_batch_scan_progress,
    pause_batch_scan,
    resume_batch_scan,
    stop_batch_scan,
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

# Configuration - ALL PATHS FROM CENTRAL path_setup.py
# NO PATH CALCULATIONS HERE!
import sys
sys.path.insert(0, "/project/src")
sys.path.insert(0, "/SimpleSecCheck/src")
from core.path_setup import (
    get_webui_base_dir,
    get_webui_cli_script,
    get_webui_results_dir,
    get_webui_logs_dir,
    get_webui_owasp_data_dir,
    get_webui_frontend_paths,
    get_owasp_data_path_host
)

BASE_DIR = get_webui_base_dir()
CLI_SCRIPT = get_webui_cli_script()
RESULTS_DIR = get_webui_results_dir()
LOGS_DIR = get_webui_logs_dir()
OWASP_DATA_DIR = get_webui_owasp_data_dir()
# Get host path for OWASP data (for database existence checks)
OWASP_DATA_DIR_HOST = get_owasp_data_path_host()

# CLI script is only needed for direct CLI usage (not for WebUI)
# WebUI calls docker-compose directly, so this validation is optional
if CLI_SCRIPT and not CLI_SCRIPT.exists() and os.path.exists("/app"):
    # Running in container (WebUI) - script not needed
    pass
elif CLI_SCRIPT and not CLI_SCRIPT.exists():
    # Running on host without script - warn but don't fail (WebUI doesn't need it)
    print(f"[WARNING] CLI script not found: {CLI_SCRIPT} (WebUI will use docker-compose directly)")

app = FastAPI(title="SimpleSecCheck WebUI", version="1.0.0")

# Environment detection
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev").lower()
IS_PRODUCTION = ENVIRONMENT == "prod"

# CORS configuration
cors_origins = os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if os.getenv("CORS_ALLOWED_ORIGINS") else []
if not cors_origins or cors_origins == [""]:
    # Default to localhost for development
    cors_origins = ["http://localhost:8080", "http://127.0.0.1:8080"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins else ["*"],  # In production, should be specific origins
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

# Production: Start scanner worker
if IS_PRODUCTION:
    @app.on_event("startup")
    async def startup_event():
        """Start scanner worker on application startup"""
        try:
            await start_scanner_worker()
            print("[Main] Scanner worker started")
        except Exception as e:
            print(f"[Main] Failed to start scanner worker: {e}")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Stop scanner worker on application shutdown"""
        try:
            await stop_scanner_worker()
            print("[Main] Scanner worker stopped")
        except Exception as e:
            print(f"[Main] Error stopping scanner worker: {e}")


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
async def start_scan(request: ScanRequest, http_request: Request):
    """
    Start a scan by calling scripts/run-docker.sh
    In Production: Adds scan to queue instead of starting directly
    In Development: Starts scan immediately (single-shot)
    """
    update_activity()
    
    # Production: Use queue system
    if IS_PRODUCTION:
        # Check if only Git scans are allowed
        only_git_scans = os.getenv("ONLY_GIT_SCANS", "true").lower() == "true"
        if only_git_scans and request.type != "code":
            raise HTTPException(
                status_code=400,
                detail=f"Only Git scans (code type) are allowed in production mode. Requested type: {request.type}"
            )
        
        # Validate Git URL
        from app.services.git_service import is_git_url
        if request.type == "code" and not is_git_url(request.target):
            raise HTTPException(
                status_code=400,
                detail="Only Git repository URLs are allowed in production mode"
            )
        
        # Get session ID from request state (set by middleware)
        session_id = getattr(http_request.state, "session_id", None)
        if not session_id:
            raise HTTPException(status_code=401, detail="Session required")
        
        # Check rate limits
        session_service = await get_session_service()
        allowed, error_msg = await session_service.check_rate_limit(session_id)
        if not allowed:
            raise HTTPException(status_code=429, detail=error_msg)
        
        # Add to queue
        queue_service = await get_queue_service()
        
        # Extract branch and commit hash from request if available
        branch = request.git_branch
        commit_hash = None  # TODO: Extract from Git if needed
        
        result = await queue_service.add_scan_to_queue(
            session_id=session_id,
            repository_url=request.target,
            branch=branch,
            commit_hash=commit_hash,
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result.get("message", "Failed to add to queue"))
        
        # Increment scan count
        await session_service.increment_scan_count(session_id)
        
        return ScanStatus(
            status="queued",
            scan_id=None,  # Will be set when scan starts
            message=result.get("message", "Scan added to queue"),
        )
    
    # Development: Start scan immediately
    else:
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
    
    # Collect all findings (with policy filtering)
    findings = collect_findings_from_results(results_dir, base_dir=BASE_DIR)
    
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
    # IMPORTANT: In container, we can only access mounted volumes, not host paths!
    # The container path is /app/owasp-dependency-check-data (mounted from host)
    # We should use the container path for checks, not the host path
    owasp_data_dir_for_check = OWASP_DATA_DIR
    
    return get_update_status_service(owasp_data_dir_for_check)


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


# ============================================================================
# Bulk Scan & GitHub API Endpoints
# ============================================================================

@app.get("/api/github/rate-limit")
async def get_github_rate_limit():
    """Get current GitHub API rate limit information"""
    update_activity()
    rate_limit = get_rate_limit_info()
    return rate_limit.to_dict()


@app.get("/api/github/repos")
async def get_github_repositories(
    username: str,
    include_private: bool = False,
    max_repos: int = 100
):
    """
    List repositories for a GitHub user or organization.
    
    Args:
        username: GitHub username or organization name
        include_private: Include private repositories (requires token)
        max_repos: Maximum number of repositories to fetch (default 100, max 100)
    """
    update_activity()
    
    # Validate max_repos
    max_repos = min(max(1, max_repos), 100)
    
    try:
        # Try as organization first, then as user
        try:
            repos, rate_limit = await list_org_repositories(username, max_repos)
        except HTTPException as e:
            if e.status_code == 404:
                # Not an org, try as user
                repos, rate_limit = await list_user_repositories(username, include_private, max_repos)
            else:
                raise
        
        return {
            "repositories": [repo.to_dict() for repo in repos],
            "rate_limit": rate_limit.to_dict(),
            "count": len(repos)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch repositories: {str(e)}")


@app.post("/api/github/validate-token")
async def validate_github_token_endpoint(token: str):
    """Validate a GitHub token"""
    update_activity()
    is_valid, user_info = await validate_github_token(token)
    return {
        "valid": is_valid,
        "user_info": user_info if is_valid else None
    }


@app.post("/api/bulk/start", response_model=BatchScanProgress)
async def start_bulk_scan(request: BatchScanRequest):
    """Start a batch scan for multiple repositories"""
    update_activity()
    return await start_batch_scan(request, BASE_DIR, RESULTS_DIR, CLI_SCRIPT)


@app.get("/api/bulk/status", response_model=BatchScanProgress)
async def get_bulk_scan_status(batch_id: str = None):
    """Get status of current batch scan"""
    update_activity()
    progress = get_batch_scan_progress(batch_id)
    if not progress:
        raise HTTPException(status_code=404, detail="No batch scan found")
    return progress


@app.post("/api/bulk/pause")
async def pause_bulk_scan():
    """Pause the current batch scan"""
    update_activity()
    await pause_batch_scan()
    progress = get_batch_scan_progress()
    if not progress:
        raise HTTPException(status_code=404, detail="No batch scan found")
    return progress


@app.post("/api/bulk/resume")
async def resume_bulk_scan():
    """Resume a paused batch scan"""
    update_activity()
    await resume_batch_scan()
    progress = get_batch_scan_progress()
    if not progress:
        raise HTTPException(status_code=404, detail="No batch scan found")
    return progress


@app.post("/api/bulk/stop")
async def stop_bulk_scan():
    """Stop the current batch scan"""
    update_activity()
    await stop_batch_scan()
    progress = get_batch_scan_progress()
    if not progress:
        raise HTTPException(status_code=404, detail="No batch scan found")
    return progress


# ============================================================================
# Production: Queue & Session Endpoints
# ============================================================================

@app.get("/api/session")
async def get_session_info(http_request: Request):
    """Get current session information"""
    if not IS_PRODUCTION:
        return {"session_id": None, "mode": "development"}
    
    session_id = getattr(http_request.state, "session_id", None)
    if not session_id:
        return {"session_id": None, "mode": "production"}
    
    session_service = await get_session_service()
    session = await session_service.validate_session(session_id)
    
    if not session:
        return {"session_id": None, "mode": "production", "valid": False}
    
    return {
        "session_id": session_id,
        "mode": "production",
        "valid": True,
        "scans_requested": session.get("scans_requested", 0),
        "rate_limit_scans": session.get("rate_limit_scans", 10),
    }


@app.post("/api/queue/add")
async def add_to_queue(
    repository_url: str,
    branch: str = None,
    http_request: Request = None,
):
    """Add scan to queue (Production only)"""
    if not IS_PRODUCTION:
        raise HTTPException(status_code=400, detail="Queue system only available in production mode")
    
    # Get session ID
    if not http_request:
        raise HTTPException(status_code=500, detail="Request object not available")
    
    session_id = getattr(http_request.state, "session_id", None)
    if not session_id:
        raise HTTPException(status_code=401, detail="Session required")
    
    # Check rate limits
    session_service = await get_session_service()
    allowed, error_msg = await session_service.check_rate_limit(session_id)
    if not allowed:
        raise HTTPException(status_code=429, detail=error_msg)
    
    # Validate Git URL
    from app.services.git_service import is_git_url
    if not is_git_url(repository_url):
        raise HTTPException(status_code=400, detail="Only Git repository URLs are allowed")
    
    # Add to queue
    queue_service = await get_queue_service()
    result = await queue_service.add_scan_to_queue(
        session_id=session_id,
        repository_url=repository_url,
        branch=branch,
        commit_hash=None,  # TODO: Extract from Git if needed
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result.get("message", "Failed to add to queue"))
    
    # Increment scan count
    await session_service.increment_scan_count(session_id)
    
    return result


@app.get("/api/queue")
async def get_queue(limit: int = 100):
    """Get public queue (anonymized)"""
    if not IS_PRODUCTION:
        return {"queue": [], "message": "Queue system only available in production mode"}
    
    queue_service = await get_queue_service()
    queue = await queue_service.get_public_queue(limit=limit)
    queue_length = await queue_service.get_queue_length()
    
    return {
        "queue": queue,
        "queue_length": queue_length,
        "max_queue_length": int(os.getenv("MAX_QUEUE_LENGTH", "1000")),
    }


@app.get("/api/queue/{queue_id}/status")
async def get_queue_status(queue_id: str, http_request: Request = None):
    """Get status of a queue item"""
    if not IS_PRODUCTION:
        raise HTTPException(status_code=400, detail="Queue system only available in production mode")
    
    queue_service = await get_queue_service()
    queue_item = await queue_service.get_queue_status(queue_id)
    
    if not queue_item:
        raise HTTPException(status_code=404, detail="Queue item not found")
    
    # Check if user owns this queue item (if session available)
    session_id = getattr(http_request.state, "session_id", None) if http_request else None
    if session_id and queue_item.get("session_id") == session_id:
        # Return full details for owner
        return queue_item
    else:
        # Return anonymized version for others
        return {
            "queue_id": queue_item["queue_id"],
            "repository_name": queue_item["repository_name"],
            "status": queue_item["status"],
            "position": queue_item.get("position"),
            "created_at": queue_item.get("created_at"),
        }


@app.get("/api/queue/my-scans")
async def get_my_scans(http_request: Request):
    """Get queue items for current session"""
    if not IS_PRODUCTION:
        return {"scans": []}
    
    session_id = getattr(http_request.state, "session_id", None)
    if not session_id:
        raise HTTPException(status_code=401, detail="Session required")
    
    queue_service = await get_queue_service()
    scans = await queue_service.get_user_queue(session_id)
    
    return {"scans": scans}


@app.get("/api/statistics")
async def get_statistics():
    """Get aggregated statistics"""
    if not IS_PRODUCTION:
        return {"message": "Statistics only available in production mode"}
    
    from app.database import get_database
    db = get_database()
    await db.initialize()
    
    try:
        stats = await db.get_statistics()
        return stats
    finally:
        await db.close()


# Serve frontend static files (after API routes)
# ALL PATHS FROM CENTRAL path_setup.py
frontend_paths = get_webui_frontend_paths()

for frontend_dir in frontend_paths:
    if frontend_dir and frontend_dir.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="static")
        break


if __name__ == "__main__":
    import uvicorn
    # Security: Default to localhost, allow override via environment variable for Docker
    # In Docker containers, set HOST=0.0.0.0 to allow external access
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host=host, port=port)
