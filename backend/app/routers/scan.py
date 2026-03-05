"""
Scan Routes
"""
import os
import uuid
import json
import asyncio
import subprocess
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
import httpx
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
from app.services.websocket_manager import get_websocket_manager
from app.services.step_service import read_steps_from_db, upsert_steps_from_log

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


@router.get("/api/scanners")
async def get_scanners(scan_type: str = None):
    """
    Get list of available scanners (dynamically from ScannerRegistry)
    
    Args:
        scan_type: Optional filter by scan type ('code', 'image', 'website', 'network')
    
    Returns:
        List of scanners with metadata
    """
    update_activity()
    if os.getenv("SCANNER_PROXY_MODE", "false").lower() == "true":
        worker_url = os.getenv("SCANNER_WORKER_API_URL", "http://backend:8080/api/scanners")
        params = {"scan_type": scan_type} if scan_type else None

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(worker_url, params=params)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"[Get Scanners] Proxy error: {e}")
            return {"scanners": []}

    import sys
    scanner_root = os.getenv("SCANNER_ROOT", "/scanner")
    if "/app" not in sys.path:
        sys.path.insert(0, "/app")
    if scanner_root and scanner_root not in sys.path:
        sys.path.insert(0, scanner_root)
    from scanner.core.scanner_registry import ScannerRegistry, ScanType
    
    # Get all scanners or filter by type
    if scan_type:
        try:
            scan_type_enum = ScanType(scan_type)
            scanners = ScannerRegistry.get_scanners_for_type(scan_type_enum)
        except ValueError:
            # Invalid scan type, return empty list
            return {"scanners": []}
    else:
        scanners = ScannerRegistry.get_all_scanners()
    
    # Format for frontend
    result = []
    for scanner in scanners:
        scan_types = sorted({capability.scan_type.value for capability in scanner.capabilities})
        result.append({
            "name": scanner.name,
            "scan_types": scan_types,
            "priority": scanner.priority,
            "requires_condition": scanner.requires_condition,
            "enabled": scanner.enabled
        })
    
    # Sort by priority
    result.sort(key=lambda x: x["priority"])
    
    return {"scanners": result}


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
        if only_git_scans and request.type not in {"code", "image"}:
            print(f"[Scan Start] Error: Only Git scans allowed, got type={request.type}")
            raise HTTPException(
                status_code=400,
                detail=f"Only Git scans (code type) or image scans are allowed in production mode. Requested type: {request.type}"
            )
        
        # Validate Git URL (image targets are allowed, validated in scan service)
        from app.services.git_service import is_git_url
        from app.services.target_service import is_docker_image_ref
        if request.type == "code" and not is_git_url(request.target) and not is_docker_image_ref(request.target):
            print(f"[Scan Start] Error: Not a Git URL or image: {request.target}")
            raise HTTPException(
                status_code=400,
                detail="Only Git repository URLs or Docker images are allowed in production mode"
            )
        if request.type == "image" and not is_docker_image_ref(request.target):
            print(f"[Scan Start] Error: Not a Docker image: {request.target}")
            raise HTTPException(
                status_code=400,
                detail="Only Docker images are allowed for image scans"
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
    print(f"[Scan Start] Adding to queue: repository_url={request.target}, branch={request.git_branch}, selected_scanners={request.selected_scanners}")
    
    # Extract branch and commit hash from request if available
    branch = request.git_branch
    commit_hash = None
    if branch and request.type == "code":
        try:
            git_url = request.target
            if not git_url.startswith("git@") and not git_url.endswith(".git") and not git_url.endswith("/"):
                git_url = f"{git_url}.git"
            result = subprocess.run(
                ["git", "ls-remote", "--heads", git_url, branch],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                commit_hash = result.stdout.split()[0].strip()
                print(f"[Scan Start] Resolved commit hash for {branch}: {commit_hash}")
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                print(f"[Scan Start] Commit hash lookup failed: {error_msg}")
        except Exception as exc:
            print(f"[Scan Start] Commit hash lookup error: {exc}")
    
    result = await queue_service.add_scan_to_queue(
        session_id=session_id,
        repository_url=request.target,
        branch=branch,
        commit_hash=commit_hash,
        selected_scanners=request.selected_scanners,
        finding_policy=request.finding_policy,
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


@router.websocket("/api/scan/stream")
async def websocket_scan_updates(websocket: WebSocket, scan_id: str = None):
    """
    WebSocket endpoint for real-time scan updates (steps ONLY, NO logs)
    Hybrid approach: Log file for persistence + direct WebSocket for real-time
    
    IMPORTANT: scan_id parameter is IGNORED if it's a UUID (queue_id).
    Always gets real scan_id (timestamp) from queue to find logs directory.
    """
    await websocket.accept()
    update_activity()
    
    ws_manager = get_websocket_manager()
    actual_scan_id = None
    
    step_stream_task: Optional[asyncio.Task] = None
    step_stream_running = True

    async def stream_steps_periodically(active_scan_id: str):
        """Send step updates periodically from DB so UI stays realtime."""
        last_snapshot = None
        while step_stream_running:
            try:
                if steps_log_file and steps_log_file.exists():
                    await upsert_steps_from_log(active_scan_id, steps_log_file.parent.parent)

                steps = await read_steps_from_db(active_scan_id)
                if steps:
                    total_steps = max([s["number"] for s in steps], default=0)
                    if total_steps == 0:
                        progress_percentage = 0
                    else:
                        completed = sum(1 for s in steps if s.get("status") == "completed")
                        running = sum(1 for s in steps if s.get("status") == "running")
                        failed = sum(1 for s in steps if s.get("status") == "failed")
                        progress_percentage = round(((completed + failed + (running * 0.5)) / total_steps) * 100)

                    snapshot = (progress_percentage, tuple((s.get("number"), s.get("status")) for s in steps))
                    if snapshot != last_snapshot:
                        await websocket.send_json({
                            "type": "step_update",
                            "steps": steps,
                            "total_steps": total_steps,
                            "progress_percentage": progress_percentage,
                            "scan_id": active_scan_id,
                            "timestamp": asyncio.get_event_loop().time()
                        })
                        last_snapshot = snapshot
            except Exception as e:
                print(f"[WebSocket] Error streaming steps: {e}")

            await asyncio.sleep(0.5)

    try:
        # Check if scan_id parameter is a UUID (queue_id) - if so, get scan_id from queue
        is_uuid = False
        if scan_id:
            uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            is_uuid = bool(re.match(uuid_pattern, scan_id, re.IGNORECASE))
        
        if is_uuid:
            # scan_id is actually a queue_id (UUID), get scan_id (timestamp) from queue
            print(f"[WebSocket] Parameter is UUID (queue_id): {scan_id}, getting scan_id from queue")
            queue_service = await get_queue_service()
            queue_item = await queue_service.get_queue_status(scan_id)
            
            if not queue_item:
                print(f"[WebSocket] Error: Queue item not found for queue_id={scan_id}")
                await websocket.send_json({"error": "Queue item not found"})
                await websocket.close()
                return
            
            actual_scan_id = queue_item.get("scan_id")
            print(f"[WebSocket] Found queue item: queue_id={scan_id}, scan_id={actual_scan_id}, status={queue_item.get('status')}")
            
            if not actual_scan_id:
                print(f"[WebSocket] Warning: scan_id not set yet for queue_id={scan_id}, scan not started")
                await websocket.send_json({"error": "Scan not started yet (scan_id not set)"})
                await websocket.close()
                return
        else:
            # scan_id is already a timestamp, use it directly
            actual_scan_id = scan_id
            print(f"[WebSocket] Using scan_id parameter directly (timestamp): {actual_scan_id}")
        
        if not actual_scan_id:
            await websocket.send_json({"error": "No scan_id provided or invalid"})
            await websocket.close()
            return
        
        print(f"[WebSocket] Connecting: scan_id={actual_scan_id}")
        
        # Connect to WebSocket manager
        await ws_manager.connect(websocket, actual_scan_id)
        
        # Send initial steps from DB (Recovery: if user reconnects)
        steps_log_file = None
        if RESULTS_DIR and RESULTS_DIR.exists():
            for scan_dir in sorted(RESULTS_DIR.iterdir(), reverse=True):
                if scan_dir.is_dir() and actual_scan_id in scan_dir.name:
                    steps_log_file = scan_dir / "logs" / "steps.log"
                    break
        if steps_log_file and steps_log_file.exists():
            await upsert_steps_from_log(actual_scan_id, steps_log_file.parent.parent)

        steps = await read_steps_from_db(actual_scan_id)

        if steps:
            # Calculate total_steps and progress_percentage from steps
            total_steps = max([s["number"] for s in steps], default=0)
            if total_steps == 0:
                progress_percentage = 0
            else:
                completed = sum(1 for s in steps if s.get("status") == "completed")
                running = sum(1 for s in steps if s.get("status") == "running")
                failed = sum(1 for s in steps if s.get("status") == "failed")
                # Progress = (completed + failed + (running * 0.5)) / total_steps
                progress_percentage = round(((completed + failed + (running * 0.5)) / total_steps) * 100)

            # Send initial steps
            await websocket.send_json({
                "type": "initial_steps",
                "steps": steps,
                "total_steps": total_steps,
                "progress_percentage": progress_percentage,
                "scan_id": actual_scan_id,
                "timestamp": asyncio.get_event_loop().time()
            })
        
        # Start periodic DB streaming for realtime updates
        step_stream_task = asyncio.create_task(stream_steps_periodically(actual_scan_id))

        # Keep connection alive and wait for updates from WebSocket manager
        # The manager will send updates directly when scanner_worker writes steps
        while True:
            # Heartbeat: wait for ping or timeout
            try:
                # Wait for ping from client (or timeout after 30 seconds)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Echo ping as pong
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat"})
            except WebSocketDisconnect:
                break
            
    except WebSocketDisconnect:
        print(f"[WebSocket] Client disconnected: scan_id={actual_scan_id}")
    except Exception as e:
        print(f"[WebSocket] Error: {e}")
    finally:
        step_stream_running = False
        if step_stream_task:
            step_stream_task.cancel()
        if actual_scan_id:
            await ws_manager.disconnect(websocket, actual_scan_id)


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
