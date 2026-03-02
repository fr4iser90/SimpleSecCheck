"""
Scan Routes
"""
import os
import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from app.services import (
    update_activity,
    ScanRequest,
    ScanStatus,
    get_scan_status as get_scan_status_service,
    stop_scan as stop_scan_service,
)
from app.services.ai_prompt_service import collect_findings_from_results, generate_ai_prompt
from app.services.queue_service import get_queue_service
from app.services.session_service import get_session_service

router = APIRouter()

# Will be injected from main
IS_PRODUCTION = None
SESSION_MANAGEMENT = None
RESULTS_DIR = None
BASE_DIR = None
current_scan = None


def init_scan_router(is_production: bool, session_management: bool, results_dir: Path, base_dir: Path, scan_state: dict):
    """Initialize router with dependencies"""
    global IS_PRODUCTION, SESSION_MANAGEMENT, RESULTS_DIR, BASE_DIR, current_scan
    IS_PRODUCTION = is_production
    SESSION_MANAGEMENT = session_management
    RESULTS_DIR = results_dir
    BASE_DIR = base_dir
    current_scan = scan_state


@router.post("/api/scan/start", response_model=ScanStatus)
async def start_scan(request: ScanRequest, http_request: Request):
    """
    Start a scan by adding it to the queue (ALWAYS uses queue system).
    Queue system works in both Dev and Prod:
    - Dev: Uses File-Database, no session/rate limiting required
    - Prod: Uses PostgreSQL, requires session/rate limiting
    Scanner worker processes scans from queue sequentially.
    """
    update_activity()
    
    # Check if only Git scans are allowed (only in Production)
    if IS_PRODUCTION:
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
    
    # Get session ID from request state (set by middleware) or create one if not available
    session_id = getattr(http_request.state, "session_id", None)
    if not session_id:
        if SESSION_MANAGEMENT:
            raise HTTPException(status_code=401, detail="Session required")
        else:
            # In Dev without session management, create a temporary session ID
            session_id = str(uuid.uuid4())
    
    # Check rate limits (only if session management is enabled)
    if SESSION_MANAGEMENT:
        session_service = await get_session_service()
        allowed, error_msg = await session_service.check_rate_limit(session_id)
        if not allowed:
            raise HTTPException(status_code=429, detail=error_msg)
    
    # Add to queue (always enabled)
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
    
    # Increment scan count (only if session management is enabled)
    if SESSION_MANAGEMENT:
        session_service = await get_session_service()
        await session_service.increment_scan_count(session_id)
    
    # Return queue_id as scan_id for tracking
    return ScanStatus(
        status="queued",
        scan_id=result.get("queue_id"),  # Use queue_id as scan_id for tracking
        message=result.get("message", "Scan added to queue"),
    )


@router.get("/api/scan/status", response_model=ScanStatus)
async def get_scan_status(http_request: Request = None):
    """Get current scan status"""
    update_activity()
    
    # Queue is always enabled, so check queue for latest scan if session available
    # Otherwise fallback to current_scan (for Dev without session)
    session_id = None
    if http_request:
        session_id = getattr(http_request.state, "session_id", None)
    
    if session_id:
        # Get user's latest scan from queue
        queue_service = await get_queue_service()
        user_scans = await queue_service.get_user_queue(session_id)
        
        if user_scans:
            # Get the most recent scan
            latest_scan = sorted(user_scans, key=lambda x: x.get("created_at", ""), reverse=True)[0]
            status = latest_scan.get("status", "unknown")
            scan_id = latest_scan.get("scan_id") or latest_scan.get("queue_id")
            
            return ScanStatus(
                status=status,
                scan_id=scan_id,
                results_dir=latest_scan.get("results_dir"),
                started_at=latest_scan.get("started_at"),
                error_code=None,
                error_message=latest_scan.get("error_message")
            )
    
    # Fallback to current_scan (for Dev or when no session)
    return await get_scan_status_service(current_scan, RESULTS_DIR)


@router.post("/api/scan/stop", response_model=ScanStatus)
async def stop_scan():
    """Stop the currently running scan"""
    update_activity()
    return await stop_scan_service(current_scan)


@router.get("/api/scan/logs")
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


@router.get("/api/scan/report")
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


@router.get("/api/scan/ai-prompt")
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
