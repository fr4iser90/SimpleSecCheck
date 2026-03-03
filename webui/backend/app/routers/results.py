"""
Results Routes
"""
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from app.services import update_activity

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
