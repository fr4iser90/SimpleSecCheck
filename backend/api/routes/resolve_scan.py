"""
POST /api/v1/resolve-scan — agent-oriented: findings if repo is current, else start scan.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status as fastapi_status
from pydantic import BaseModel, Field

from api.deps.actor_context import get_authenticated_user, ActorContext
from api.schemas.scan_schemas import ScanFindingsResponseSchema
from application.services.resolve_scan_service import ResolveScanService
from domain.exceptions.scan_exceptions import (
    ScanConcurrencyLimitException,
    ScanExecutionRateLimitException,
    ScanPolicyBlockedException,
    FeatureDisabledException,
    TargetPermissionDeniedException,
    ScanValidationException,
)

router = APIRouter(
    prefix="/api/v1",
    tags=["resolve-scan"],
    responses={
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        429: {"description": "Too Many Requests"},
        500: {"description": "Internal Server Error"},
    },
)


class ResolveScanRequestSchema(BaseModel):
    repo_url: str = Field(..., min_length=1, max_length=2000, description="Git repository URL")
    branch: Optional[str] = Field(
        None,
        max_length=255,
        description="Branch to scan (defaults to target/repo branch or main)",
    )
    check_commit: bool = Field(
        default=True,
        description="If true, compare remote HEAD to last scan commit before returning findings",
    )
    force_scan: bool = Field(
        default=False,
        description="If true, always enqueue a new scan (ignore existing findings)",
    )
    findings_limit: Optional[int] = Field(
        None,
        ge=1,
        le=200,
        description="When status=ready, max findings returned inline (paginated)",
    )
    findings_offset: int = Field(
        default=0,
        ge=0,
        description="Pagination offset for inline findings and findings_poll_path",
    )
    findings_severity: Optional[str] = Field(
        None,
        description="Comma-separated severities for findings, e.g. CRITICAL,HIGH",
    )


class ResolveScanResponseSchema(BaseModel):
    status: str = Field(description="ready | scanning | started")
    scan_id: str
    repo_url: str
    branch: str
    message: str
    commit_sha: Optional[str] = None
    target_id: Optional[str] = None
    github_repo_id: Optional[str] = None
    progress: Optional[float] = Field(None, ge=0, le=100)
    status_poll_path: str = Field(
        description="Relative path to poll scan status until completed",
    )
    findings_poll_path: str = Field(
        description="Relative path to fetch findings after scan completes",
    )
    findings: Optional[ScanFindingsResponseSchema] = None


def _resolve_service() -> ResolveScanService:
    return ResolveScanService()


@router.post(
    "/resolve-scan",
    response_model=ResolveScanResponseSchema,
    summary="Resolve repo scan for agents",
    description=(
        "Single entry for automation: if the latest completed scan matches the current "
        "branch HEAD (git ls-remote), returns findings immediately. Otherwise starts a "
        "new scan and returns scan_id — poll status_poll_path until completed, then "
        "findings_poll_path. Requires API key or user JWT."
    ),
    responses={
        200: {"description": "Findings ready (status=ready) or scan already running (status=scanning)"},
        202: {"description": "New scan started (status=started)"},
    },
)
async def resolve_scan(
    body: ResolveScanRequestSchema,
    response: Response,
    actor_context: ActorContext = Depends(get_authenticated_user),
    svc: ResolveScanService = Depends(_resolve_service),
) -> ResolveScanResponseSchema:
    if not actor_context.user_id:
        raise HTTPException(
            status_code=fastapi_status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        result = await svc.resolve(
            actor_context.user_id,
            body.repo_url,
            branch=body.branch,
            check_commit=body.check_commit,
            force_scan=body.force_scan,
            actor_role=actor_context.role or "user",
            findings_limit=body.findings_limit,
            findings_offset=body.findings_offset,
            findings_severity=body.findings_severity,
        )
    except ScanConcurrencyLimitException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )
    except ScanExecutionRateLimitException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
            headers={"Retry-After": str(getattr(e, "retry_after_seconds", 3600))},
        )
    except ScanPolicyBlockedException as e:
        raise HTTPException(status_code=fastapi_status.HTTP_403_FORBIDDEN, detail=str(e))
    except FeatureDisabledException as e:
        raise HTTPException(status_code=fastapi_status.HTTP_403_FORBIDDEN, detail=str(e))
    except TargetPermissionDeniedException as e:
        raise HTTPException(status_code=fastapi_status.HTTP_403_FORBIDDEN, detail=str(e))
    except ScanValidationException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    from application.helpers.findings_pagination import build_findings_poll_path

    sid = result.scan_id
    poll_status = f"/api/v1/scans/{sid}/status"
    poll_findings = build_findings_poll_path(
        sid,
        limit=body.findings_limit,
        offset=body.findings_offset,
        severity=body.findings_severity,
    )

    payload = ResolveScanResponseSchema(
        status=result.status,
        scan_id=sid,
        repo_url=result.repo_url,
        branch=result.branch,
        message=result.message,
        commit_sha=result.commit_sha,
        target_id=result.target_id,
        github_repo_id=result.github_repo_id,
        progress=result.progress,
        status_poll_path=poll_status,
        findings_poll_path=poll_findings,
        findings=result.findings_response,
    )

    if result.status == "started":
        response.status_code = fastapi_status.HTTP_202_ACCEPTED

    return payload
