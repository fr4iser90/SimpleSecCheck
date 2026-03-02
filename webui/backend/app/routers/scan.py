"""
Scan Routes
"""
import os
import uuid
import json
import asyncio
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
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
    print(f"[Scan Start] Request received: type={request.type}, target={request.target}")
    update_activity()
    
    # Check if only Git scans are allowed (only in Production)
    if IS_PRODUCTION:
        only_git_scans = os.getenv("ONLY_GIT_SCANS", "true").lower() == "true"
        if only_git_scans and request.type != "code":
            print(f"[Scan Start] Error: Only Git scans allowed, got type={request.type}")
            raise HTTPException(
                status_code=400,
                detail=f"Only Git scans (code type) are allowed in production mode. Requested type: {request.type}"
            )
        
        # Validate Git URL
        from app.services.git_service import is_git_url
        if request.type == "code" and not is_git_url(request.target):
            print(f"[Scan Start] Error: Not a Git URL: {request.target}")
            raise HTTPException(
                status_code=400,
                detail="Only Git repository URLs are allowed in production mode"
            )
    
    # Get session ID from request state (set by middleware) or create one if not available
    session_id = getattr(http_request.state, "session_id", None)
    print(f"[Scan Start] Session ID: {session_id}, SESSION_MANAGEMENT={SESSION_MANAGEMENT}")
    if not session_id:
        if SESSION_MANAGEMENT:
            print(f"[Scan Start] Error: No session ID, SESSION_MANAGEMENT={SESSION_MANAGEMENT}")
            raise HTTPException(status_code=401, detail="Session required")
        else:
            # In Dev without session management, create a temporary session ID
            session_id = str(uuid.uuid4())
            print(f"[Scan Start] Created temporary session ID: {session_id}")
    
    # Check rate limits (only if session management is enabled)
    if SESSION_MANAGEMENT:
        session_service = await get_session_service()
        allowed, error_msg = await session_service.check_rate_limit(session_id)
        if not allowed:
            print(f"[Scan Start] Error: Rate limit exceeded: {error_msg}")
            raise HTTPException(status_code=429, detail=error_msg)
    
    # Add to queue (always enabled)
    queue_service = await get_queue_service()
    print(f"[Scan Start] Adding to queue: repository_url={request.target}, branch={request.git_branch}")
    
    # Extract branch and commit hash from request if available
    branch = request.git_branch
    commit_hash = None  # TODO: Extract from Git if needed
    
    result = await queue_service.add_scan_to_queue(
        session_id=session_id,
        repository_url=request.target,
        branch=branch,
        commit_hash=commit_hash,
    )
    
    print(f"[Scan Start] Queue result: {result}")
    
    if "error" in result:
        print(f"[Scan Start] Error adding to queue: {result.get('message')}")
        raise HTTPException(status_code=400, detail=result.get("message", "Failed to add to queue"))
    
    # Increment scan count (only if session management is enabled)
    if SESSION_MANAGEMENT:
        session_service = await get_session_service()
        await session_service.increment_scan_count(session_id)
    
    # Return queue_id as scan_id for tracking
    # Use "pending" status to match queue status (consistent with frontend expectations)
    print(f"[Scan Start] Success: queue_id={result.get('queue_id')}")
    return ScanStatus(
        status="pending",
        scan_id=result.get("queue_id"),  # Use queue_id as scan_id for tracking
        message=result.get("message", "Scan added to queue"),
    )


@router.get("/api/scan/status", response_model=ScanStatus)
async def get_scan_status(http_request: Request = None):
    """Get current scan status"""
    update_activity()
    
    session_id = None
    if http_request:
        session_id = getattr(http_request.state, "session_id", None)
    
    if not session_id:
        return ScanStatus(
            status="idle",
            scan_id=None,
            message="No session found"
        )
    
    queue_service = await get_queue_service()
    user_scans = await queue_service.get_user_queue(session_id)
    
    if not user_scans:
        return ScanStatus(
            status="idle",
            scan_id=None,
            message="No scans found"
        )
    
    latest_scan = sorted(user_scans, key=lambda x: x.get("created_at", ""), reverse=True)[0]
    status = latest_scan.get("status", "unknown")
    scan_id = latest_scan.get("scan_id")
    
    return ScanStatus(
        status=status,
        scan_id=scan_id,
        results_dir=latest_scan.get("results_dir"),
        started_at=latest_scan.get("started_at"),
        error_code=None,
        error_message=latest_scan.get("error_message")
    )


@router.post("/api/scan/stop", response_model=ScanStatus)
async def stop_scan():
    """Stop the currently running scan"""
    update_activity()
    return await stop_scan_service(current_scan)


@router.get("/api/scan/logs")
async def get_logs(http_request: Request = None):
    """
    Get logs from current scan (simple polling endpoint)
    Returns all lines from results/*/logs/steps.log
    ONLY uses scan_id (timestamp) from queue, NO fallbacks
    
    See docs/QUEUE_SCAN_ID_RULES.md for details.
    """
    update_activity()
    
    scan_id = None
    
    session_id = None
    if http_request:
        session_id = getattr(http_request.state, "session_id", None)
    
    if not session_id:
        print(f"[Get Logs] Error: No session_id")
        return {"lines": [], "count": 0}
    
    queue_service = await get_queue_service()
    user_scans = await queue_service.get_user_queue(session_id)
    
    if not user_scans:
        print(f"[Get Logs] Error: No scans found for session {session_id}")
        return {"lines": [], "count": 0}
    
    latest_scan = sorted(user_scans, key=lambda x: x.get("created_at", ""), reverse=True)[0]
    scan_id = latest_scan.get("scan_id")
    queue_id_from_scan = latest_scan.get("queue_id")
    
    print(f"[Get Logs] Latest scan: queue_id={queue_id_from_scan}, scan_id={scan_id}, status={latest_scan.get('status')}")
    
    if not scan_id:
        print(f"[Get Logs] Warning: scan_id not set yet for queue_id={queue_id_from_scan}")
        return {"lines": [], "count": 0}
    
    log_file = None
    
    if RESULTS_DIR and RESULTS_DIR.exists():
        print(f"[Get Logs] Searching for scan directory with scan_id={scan_id} in {RESULTS_DIR}")
        for scan_dir in sorted(RESULTS_DIR.iterdir(), reverse=True):
            if scan_dir.is_dir() and scan_id in scan_dir.name:
                log_file = scan_dir / "logs" / "steps.log"
                print(f"[Get Logs] Found steps.log: {log_file}")
                break
        if not log_file:
            print(f"[Get Logs] Warning: No directory found with scan_id={scan_id} in {RESULTS_DIR}")
    else:
        print(f"[Get Logs] Error: RESULTS_DIR not available or doesn't exist: {RESULTS_DIR}")
    
    if log_file and log_file.exists():
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        print(f"[Get Logs] Returning {len(lines)} lines from steps.log")
        return {"lines": lines, "count": len(lines)}
    else:
        print(f"[Get Logs] Error: steps.log not found at {log_file}")
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


@router.get("/api/scan/stream")
async def stream_scan_updates(http_request: Request, scan_id: str = None):
    """
    SSE endpoint for real-time scan updates (steps ONLY, NO logs)
    
    IMPORTANT: scan_id parameter is IGNORED if it's a UUID (queue_id).
    Always gets real scan_id (timestamp) from queue to find logs directory.
    """
    update_activity()
    
    async def event_generator():
        last_step_count = -1  # Start at -1 to always send initial data
        first_iteration = True
        
        # Check if scan_id parameter is a UUID (queue_id) - if so, ignore it
        is_uuid = False
        if scan_id:
            uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            is_uuid = bool(re.match(uuid_pattern, scan_id, re.IGNORECASE))
            if is_uuid:
                print(f"[SSE Stream] Ignoring UUID parameter (queue_id): {scan_id}, will get scan_id from queue")
        
        # ALWAYS get scan_id (timestamp) from queue, NEVER use UUID parameter
        actual_scan_id = None
        
        if not http_request:
            print(f"[SSE Stream] Error: No request provided")
            yield f"data: {json.dumps({'error': 'No request provided'})}\n\n"
            return
        
        session_id = getattr(http_request.state, "session_id", None)
        if not session_id:
            print(f"[SSE Stream] Error: No session_id")
            yield f"data: {json.dumps({'error': 'No session_id'})}\n\n"
            return
        
        queue_service = await get_queue_service()
        user_scans = await queue_service.get_user_queue(session_id)
        
        if not user_scans:
            print(f"[SSE Stream] Error: No scans found for session {session_id}")
            yield f"data: {json.dumps({'error': 'No scans found'})}\n\n"
            return
        
        latest_scan = sorted(user_scans, key=lambda x: x.get("created_at", ""), reverse=True)[0]
        actual_scan_id = latest_scan.get("scan_id")
        queue_id_from_scan = latest_scan.get("queue_id")
        
        print(f"[SSE Stream] Latest scan: queue_id={queue_id_from_scan}, scan_id={actual_scan_id}, status={latest_scan.get('status')}")
        
        if not actual_scan_id:
            print(f"[SSE Stream] Warning: scan_id not set yet for queue_id={queue_id_from_scan}, scan not started")
            yield f"data: {json.dumps({'error': 'Scan not started yet (scan_id not set)'})}\n\n"
            return
        
        print(f"[SSE Stream] Using scan_id (timestamp): {actual_scan_id} to find logs directory")
        
        if not actual_scan_id:
            yield f"data: {json.dumps({'error': 'No active scan found'})}\n\n"
            return
        
        # Find steps.log file ONCE (not in every loop iteration)
        steps_log_file = None
        if RESULTS_DIR and RESULTS_DIR.exists():
            for scan_dir in sorted(RESULTS_DIR.iterdir(), reverse=True):
                if scan_dir.is_dir() and actual_scan_id in scan_dir.name:
                    steps_log_file = scan_dir / "logs" / "steps.log"
                    print(f"[SSE Stream] Using scan_id (timestamp): {actual_scan_id} to find logs directory")
                    print(f"[SSE Stream] Found steps.log: {steps_log_file}")
                    break
            if not steps_log_file:
                print(f"[SSE Stream] Warning: No directory found with scan_id={actual_scan_id} in {RESULTS_DIR}")
        else:
            print(f"[SSE Stream] Error: RESULTS_DIR not available or doesn't exist: {RESULTS_DIR}")
        
        while True:
            # Check if client disconnected
            if await http_request.is_disconnected() if http_request else False:
                break
            
            try:
                steps = []
                step_map = {}
                
                # Read steps from steps.log
                if steps_log_file and steps_log_file.exists():
                    with open(steps_log_file, "r", encoding="utf-8", errors="ignore") as f:
                        step_lines = [line.strip() for line in f.readlines() if line.strip() and not line.strip().startswith("-----")]
                    
                    for line in step_lines:
                        step_match = re.match(r'([⏳✓❌]?)\s*Step\s+(\d+):\s*(.+)', line, re.IGNORECASE)
                        if step_match:
                            status_icon, step_num_str, message = step_match.groups()
                            step_number = int(step_num_str)
                            
                            status = 'pending'
                            if status_icon == '✓':
                                status = 'completed'
                            elif status_icon == '⏳':
                                status = 'running'
                            elif status_icon == '❌':
                                status = 'failed'
                            
                            name_match = re.match(r'^(.+?)(?:\s+\.\.\.|\s+completed|$)', message, re.IGNORECASE)
                            step_name = name_match.group(1).strip() if name_match else message.strip()
                            
                            if step_number not in step_map:
                                step_map[step_number] = {
                                    "number": step_number,
                                    "name": step_name,
                                    "status": status,
                                    "message": message.strip()
                                }
                            else:
                                # Update existing step
                                step_map[step_number]["status"] = status
                                step_map[step_number]["message"] = message.strip()
                
                steps = sorted(step_map.values(), key=lambda x: x["number"])
                
                current_step_count = len(steps)
                
                # Send initial steps on first iteration OR when new steps are added
                if first_iteration or current_step_count > last_step_count:
                    data = {
                        "logs": [],
                        "steps": steps,
                        "scan_id": actual_scan_id,
                        "timestamp": asyncio.get_event_loop().time()
                    }
                    
                    yield f"data: {json.dumps(data)}\n\n"
                    
                    last_step_count = current_step_count
                    first_iteration = False
                
                # Check if scan is done (no new updates for 5 seconds)
                # This is a simple heuristic - in production you might want to check queue status
                await asyncio.sleep(0.5)  # Check every 500ms
                
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                await asyncio.sleep(1)  # Wait before retrying
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
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
