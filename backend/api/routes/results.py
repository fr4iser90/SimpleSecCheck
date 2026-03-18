"""
Results API — HTML report (summary.html).

Access: owner, report_shared_with_user_ids, or ?share_token= (report_share_token in metadata).
"""
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi import status as fastapi_status

from api.deps.actor_context import get_actor_context, ActorContext
from application.services.scan_service import ScanService
from domain.exceptions.scan_exceptions import ScanNotFoundException
from domain.services.scan_result_access import can_read_scan_results
from config.settings import get_settings
from infrastructure.container import get_scan_service

router = APIRouter(
    prefix="/api",
    tags=["results"],
    responses={404: {"description": "Not found"}, 403: {"description": "Forbidden"}},
)


def _report_path(scan_id: str) -> Path:
    s = get_settings()
    base = Path(s.RESULTS_DIR_HOST if hasattr(s, "RESULTS_DIR_HOST") else "/app/results")
    return base / scan_id / "summary" / "summary.html"


def _scan_svc():
    return get_scan_service()


async def _serve_report(
    scan_id: str,
    actor: ActorContext,
    svc: ScanService,
    share_token: Optional[str],
):
    try:
        dto = await svc.get_scan_by_id(scan_id)
    except ScanNotFoundException:
        raise HTTPException(fastapi_status.HTTP_404_NOT_FOUND, "Scan not found")

    uid = dto.user_id if dto.user_id not in (None, "") else None
    if not can_read_scan_results(
        metadata=dto.metadata or {},
        scan_user_id=str(uid) if uid else None,
        actor_user_id=actor.user_id,
        actor_session_id=actor.session_id,
        actor_is_authenticated=bool(actor.is_authenticated),
        share_token_query=share_token,
    ):
        raise HTTPException(fastapi_status.HTTP_403_FORBIDDEN, "Access denied")

    p = _report_path(scan_id)
    if not p.is_file():
        raise HTTPException(fastapi_status.HTTP_404_NOT_FOUND, "Report not found")
    return FileResponse(p, media_type="text/html", filename="summary.html")


@router.get("/results/{scan_id}/report")
async def get_results_report(
    scan_id: str,
    actor_context: ActorContext = Depends(get_actor_context),
    scan_service: ScanService = Depends(_scan_svc),
    share_token: Optional[str] = Query(None),
):
    return await _serve_report(scan_id, actor_context, scan_service, share_token)
