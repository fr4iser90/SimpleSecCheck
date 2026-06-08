"""Shared handler for GET scan findings (used by scans and user target routes)."""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from fastapi import status as fastapi_status

from api.deps.actor_context import ActorContext
from api.schemas.scan_schemas import ScanFindingsResponseSchema
from application.helpers.findings_file import load_findings_payload
from application.helpers.findings_response import build_findings_response
from application.services.scan_service import ScanService
from domain.entities.scan import ScanStatus
from domain.exceptions.scan_exceptions import ScanNotFoundException, ScanException
from domain.policies.scan_result_access_policy import can_read_scan_results


def _scan_user_id_str(dto) -> Optional[str]:
    if dto.user_id in (None, ""):
        return None
    return str(dto.user_id)


def _require_scan_read(dto, actor: ActorContext) -> None:
    if not can_read_scan_results(
        metadata=dto.metadata or {},
        scan_user_id=_scan_user_id_str(dto),
        actor_user_id=actor.user_id,
        actor_session_id=actor.session_id,
        actor_is_authenticated=bool(actor.is_authenticated),
        share_token_query=None,
    ):
        raise HTTPException(
            status_code=fastapi_status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )


async def get_scan_findings_response(
    scan_service: ScanService,
    scan_id: str,
    actor_context: ActorContext,
    *,
    limit: Optional[int] = None,
    offset: int = 0,
    severity: Optional[str] = None,
    tool: Optional[str] = None,
    path_prefix: Optional[str] = None,
    rule_id: Optional[str] = None,
) -> ScanFindingsResponseSchema:
    """Load paginated findings for a scan; raises HTTPException on errors."""
    try:
        scan_dto = await scan_service.get_scan_by_id(scan_id)
        _require_scan_read(scan_dto, actor_context)

        status_str = (
            scan_dto.status.value
            if hasattr(scan_dto.status, "value")
            else str(scan_dto.status or "")
        ).lower()

        payload, _source = load_findings_payload(scan_id)
        terminal = status_str in (
            ScanStatus.COMPLETED.value,
            ScanStatus.FAILED.value,
            ScanStatus.CANCELLED.value,
            ScanStatus.INTERRUPTED.value,
        )

        if payload is None:
            if not terminal:
                raise HTTPException(
                    status_code=fastapi_status.HTTP_409_CONFLICT,
                    detail={
                        "message": "Scan still in progress; findings not available yet",
                        "status": status_str,
                    },
                )
            raise HTTPException(
                status_code=fastapi_status.HTTP_404_NOT_FOUND,
                detail="Findings not found for this scan",
            )

        response = build_findings_response(
            scan_id,
            scan_dto,
            status_str=status_str,
            limit=limit,
            offset=offset,
            severity=severity,
            tool=tool,
            path_prefix=path_prefix,
            rule_id=rule_id,
        )
        if response is None:
            raise HTTPException(
                status_code=fastapi_status.HTTP_404_NOT_FOUND,
                detail="Findings not found for this scan",
            )
        return response
    except ScanNotFoundException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except HTTPException:
        raise
    except ScanException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
