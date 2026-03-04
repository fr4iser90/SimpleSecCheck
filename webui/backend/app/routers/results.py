"""
Results Routes
"""
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse
import os
from app.services import update_activity
from app.database import get_database

# Environment guard (read directly from runtime ENV)
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev").lower()
IS_PRODUCTION = ENVIRONMENT == "prod"

router = APIRouter()

# Will be injected from main
RESULTS_DIR = None


def init_results_router(results_dir: Path):
    """Initialize router with results directory"""
    global RESULTS_DIR
    RESULTS_DIR = results_dir


@router.get("/api/results")
async def list_results():
    """
    List all scan results (file browser)
    No database - just reads results/ directory
    """
    if IS_PRODUCTION:
        raise HTTPException(status_code=403, detail="Results endpoint disabled in production")
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


@router.get("/api/results/{scan_id}/report")
async def get_result_report(scan_id: str):
    """Get HTML report from specific scan"""
    if IS_PRODUCTION:
        raise HTTPException(status_code=403, detail="Results endpoint disabled in production")
    report_file = RESULTS_DIR / scan_id / "security-summary.html"
    
    if not report_file.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    
    return FileResponse(
        report_file,
        media_type="text/html",
        headers={"Content-Disposition": "inline"}
    )


@router.get("/api/results/{scan_id}/ai-prompt")
async def get_result_ai_prompt(
    scan_id: str,
    language: str = Query("english", description="Prompt language (english, chinese, german)"),
):
    """Get saved AI prompt JSON for a specific scan and language."""
    if IS_PRODUCTION:
        raise HTTPException(status_code=403, detail="Results endpoint disabled in production")
    update_activity()
    normalized = language.lower()
    prompt_file = RESULTS_DIR / scan_id / f"ai-prompt-{normalized}.json"

    if not prompt_file.exists():
        raise HTTPException(status_code=404, detail="AI prompt not found")

    return FileResponse(
        prompt_file,
        media_type="application/json",
        headers={"Content-Disposition": "inline"}
    )


@router.get("/api/my-results/{scan_id}/report")
async def get_my_result_report(scan_id: str, http_request: Request):
    """Get HTML report for the current session's scan (prod-safe)."""
    session_id = getattr(http_request.state, "session_id", None)
    if not session_id:
        raise HTTPException(status_code=401, detail="Session required")

    db = get_database()
    has_access = await db.has_scan_access(scan_id, session_id)
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied")

    queue_item = await db.get_queue_item(scan_id)
    if not queue_item:
        # Try to find queue item by scan_id
        try:
            queue_items = await db.get_queue_by_session(session_id)
            queue_item = next((item for item in queue_items if item.get("scan_id") == scan_id), None)
        except Exception:
            queue_item = None

    results_dir_name = queue_item.get("results_dir") if queue_item else None
    report_file = RESULTS_DIR / (results_dir_name or scan_id) / "security-summary.html"
    if not report_file.exists():
        # Fallback: scan_id is a timestamp, results directory includes project prefix
        matching_dir = None
        if RESULTS_DIR and RESULTS_DIR.exists():
            for scan_dir in RESULTS_DIR.iterdir():
                if scan_dir.is_dir() and scan_id in scan_dir.name:
                    matching_dir = scan_dir
                    break
        if matching_dir:
            report_file = matching_dir / "security-summary.html"
        if not report_file.exists():
            raise HTTPException(status_code=404, detail="Report not found")

    return FileResponse(
        report_file,
        media_type="text/html",
        headers={"Content-Disposition": "inline"}
    )
