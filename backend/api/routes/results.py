"""
Results API Routes

Serves scan report HTML (summary.html) for /api/results/{scan_id}/report
and /api/my-results/{scan_id}/report. Scanner writes reports to
results/{scan_id}/summary/summary.html.
"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi import status as fastapi_status

from api.deps.actor_context import get_actor_context, ActorContext
from application.services.scan_service import ScanService
from domain.exceptions.scan_exceptions import ScanNotFoundException
from config.settings import get_settings
from infrastructure.container import get_scan_service


router = APIRouter(
    prefix="/api",
    tags=["results"],
    responses={
        404: {"description": "Report or scan not found"},
        403: {"description": "Forbidden"},
    },
)


def _get_report_path(scan_id: str) -> Path:
    """Resolve path to summary.html for a scan. Backend container has results at /app/results."""
    settings = get_settings()
    base = Path(settings.RESULTS_DIR_HOST if hasattr(settings, "RESULTS_DIR_HOST") else "/app/results")
    return base / scan_id / "summary" / "summary.html"


@router.get(
    "/results/{scan_id}/report",
    summary="Get scan report (public)",
    description="Serve the HTML report for a scan. No ownership check.",
)
async def get_results_report(scan_id: str):
    """Serve summary.html for the given scan_id if the file exists."""
    report_path = _get_report_path(scan_id)
    if not report_path.is_file():
        raise HTTPException(
            status_code=fastapi_status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    return FileResponse(
        report_path,
        media_type="text/html",
        filename="summary.html",
    )


def _get_scan_service_dependency():
    return get_scan_service()


@router.get(
    "/my-results/{scan_id}/report",
    summary="Get my scan report",
    description="Serve the HTML report for a scan. If authenticated, only the scan owner can access.",
)
async def get_my_results_report(
    scan_id: str,
    actor_context: ActorContext = Depends(get_actor_context),
    scan_service: ScanService = Depends(_get_scan_service_dependency),
):
    """Serve summary.html for the given scan_id. When authenticated, require scan ownership."""
    try:
        scan_dto = await scan_service.get_scan_by_id(scan_id)
    except ScanNotFoundException:
        raise HTTPException(
            status_code=fastapi_status.HTTP_404_NOT_FOUND,
            detail="Scan not found",
        )
    if actor_context.is_authenticated and scan_dto.user_id != actor_context.get_identifier():
        raise HTTPException(
            status_code=fastapi_status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    report_path = _get_report_path(scan_id)
    if not report_path.is_file():
        raise HTTPException(
            status_code=fastapi_status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    return FileResponse(
        report_path,
        media_type="text/html",
        filename="summary.html",
    )
