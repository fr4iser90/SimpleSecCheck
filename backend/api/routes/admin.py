"""
Admin API Routes

Handles admin-only operations like system configuration updates.
"""
import os
from typing import Optional, Dict, Any, List
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from pydantic import BaseModel, EmailStr, Field

from api.deps.actor_context import get_admin_user, ActorContext
from infrastructure.container import (
    get_database_health,
    get_system_state_repository,
    get_scan_repository,
    get_user_service,
    get_blocked_ip_repository,
    get_scanner_repository,
    get_scanner_tool_settings_repository,
)
from domain.repositories.system_state_repository import SystemStateRepository
from domain.repositories.scan_repository import ScanRepository
from domain.repositories.blocked_ip_repository import BlockedIPRepository
from domain.repositories.scanner_repository import ScannerRepository as ScannerRepositoryInterface
from domain.repositories.scanner_tool_settings_repository import ScannerToolSettingsRepository
from application.services.user_service import UserService
from infrastructure.redis.client import get_redis_health
from domain.services.audit_log_service import AuditLogService
from domain.services.scanner_duration_service import ScannerDurationService
from domain.policies.target_permission_policy import (
    ALL_SCAN_FEATURE_FLAG_KEYS,
    ROLE_CAPABILITY_TARGET_TYPES,
    ROLE_NAMES,
)
from domain.policies.role_capabilities_policy import (
    default_role_capabilities,
    merge_role_capabilities_raw,
)
from domain.datetime_serialization import isoformat_utc
from domain.policies.finding_policy import (
    DEFAULT_FINDING_POLICY_APPLY_BY_DEFAULT,
    DEFAULT_FINDING_POLICY_PATH,
    default_scan_defaults,
)
from domain.policies.scan_profile_policy import (
    extract_profile_catalog_from_scanner_metadata,
    normalize_profile_key,
    resolve_profile_order,
    scan_profile_settings,
)
from datetime import datetime

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        500: {"description": "Internal Server Error"},
    },
)


def get_system_state_repository_dependency() -> SystemStateRepository:
    return get_system_state_repository()


def get_scan_repository_dependency() -> ScanRepository:
    return get_scan_repository()


def get_scanner_repository_dependency() -> ScannerRepositoryInterface:
    return get_scanner_repository()


class SMTPConfigRequest(BaseModel):
    """Request for SMTP configuration update."""
    
    enabled: bool = Field(description="Enable SMTP")
    host: str = Field(description="SMTP host")
    port: int = Field(description="SMTP port")
    user: str = Field(description="SMTP username/email")
    password: str = Field(description="SMTP password")
    use_tls: bool = Field(default=True, description="Use TLS")
    from_email: str = Field(description="From email address")
    from_name: str = Field(description="From name")


class SMTPConfigResponse(BaseModel):
    """Response for SMTP configuration."""
    
    enabled: bool
    host: str
    port: int
    user: str
    password: str = Field(description="Password (masked)")
    use_tls: bool
    from_email: str
    from_name: str


class SystemConfigResponse(BaseModel):
    """Response for system configuration."""

    auth_mode: str
    max_concurrent_jobs: int = Field(
        ge=1,
        le=50,
        description="Worker parallel scan jobs (restart worker after change unless using env override)",
    )
    smtp: Optional[Dict[str, Any]] = None


class WorkerJobsConfigRequest(BaseModel):
    """Update how many complete scans the worker runs in parallel."""

    max_concurrent_jobs: int = Field(ge=1, le=50)


def _default_execution_limits() -> Dict[str, Any]:
    return {
        "max_scans_per_hour_global": None,
        "max_scans_per_hour_per_user": 20,
        "max_scans_per_hour_per_guest_session": 5,
        "max_concurrent_scans_per_user": 3,
        "max_concurrent_scans_per_guest": 2,
        "rate_limit_admins": False,
        "max_scan_duration_seconds": 3600,
        "initial_scan_delay_seconds": 300,  # Delay before auto-queuing first scan for new targets (default 5 min)
    }


def _default_policies() -> Dict[str, Any]:
    return {
        "blocked_target_patterns": [],
        "blocked_scan_types": [],
        "require_auth_for_git": False,
    }


def _default_scan_defaults() -> Dict[str, Any]:
    """Default for scan form: finding policy path and whether to apply by default."""
    out = dict(default_scan_defaults())
    out.update(scan_profile_settings())
    return out


async def _scan_profile_catalog(scanner_repo: ScannerRepositoryInterface) -> List[str]:
    scanners = await scanner_repo.list_all()
    return extract_profile_catalog_from_scanner_metadata(scanners)


def _validate_profile_field(value: Optional[str], *, catalog: List[str], field_name: str) -> Optional[str]:
    if value is None:
        return None
    key = normalize_profile_key(value)
    if not key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field_name}: profile cannot be empty")
    if key not in set(catalog):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name}: invalid profile '{key}'. Allowed: {catalog}",
        )
    return key


class ScanEnforcementUpdate(BaseModel):
    """Partial update for scan rate limits, max duration, and policies."""

    execution_limits: Optional[Dict[str, Any]] = None
    policies: Optional[Dict[str, Any]] = None


class AuthConfigResponse(BaseModel):
    """Auth config: AUTH_MODE = login mechanism; ACCESS_MODE = who may use the system; allow_self_registration; registration_approval; require_email_verification; bulk_scan_allow_guests."""
    auth_mode: str = Field(description="Authentication mode (login mechanism): free | basic | jwt")
    access_mode: str = Field(description="Who may use the system: public | mixed | private")
    allow_self_registration: bool = Field(description="Allow users to self-register (sign up)")
    registration_approval: str = Field(
        default="auto",
        description="When self-registration is on: 'auto' = new users can log in immediately; 'admin_approval' = new users need admin to activate.",
    )
    require_email_verification: bool = Field(
        default=False,
        description="When enabled, users must verify their email (click link from sign-up mail) before they can log in.",
    )
    bulk_scan_allow_guests: bool = Field(default=False, description="Allow guests to use bulk scan (admin override). Default: only logged-in users.")


class AuthConfigRequest(BaseModel):
    """Request to update auth configuration."""
    auth_mode: Optional[str] = Field(None, description="free | basic | jwt")
    access_mode: Optional[str] = Field(None, description="public | mixed | private")
    allow_self_registration: Optional[bool] = None
    registration_approval: Optional[str] = Field(None, description="auto | admin_approval")
    require_email_verification: Optional[bool] = Field(None, description="Require verified email to log in")
    bulk_scan_allow_guests: Optional[bool] = Field(None, description="Allow guests to use bulk scan (admin override)")


# ---------------------------------------------------------------------------
# Role capabilities (RBAC: allowed target types, scanners, My Targets per role)
# Stored in SystemState.config["role_capabilities"]. See docs/ROLE_CAPABILITIES_SCHEMA.md.
# ---------------------------------------------------------------------------

class RoleCapabilityEntry(BaseModel):
    """Per-role capabilities: which target types and scanners the role may use; whether My Targets is allowed."""
    allowed_target_types: List[str] = Field(
        default_factory=list,
        description="Backend target type keys (e.g. git_repo, uploaded_code, container_registry). Empty = none allowed.",
    )
    allowed_scanner_tools_keys: List[str] = Field(
        default_factory=list,
        description="Scanner tools_key slugs (e.g. semgrep, trivy). Empty = no restriction (all scanners allowed).",
    )
    my_targets_allowed: bool = Field(
        default=False,
        description="Whether this role may use My Targets (create/list/delete own targets).",
    )
    my_targets_target_types: Optional[List[str]] = Field(
        default=None,
        description="If set, My Targets is restricted to these target types only; else allowed_target_types apply.",
    )


class RoleCapabilitiesResponse(BaseModel):
    """Role capabilities for all roles. GET response and shape stored in config."""
    guest: RoleCapabilityEntry = Field(default_factory=RoleCapabilityEntry)
    user: RoleCapabilityEntry = Field(default_factory=RoleCapabilityEntry)
    admin: RoleCapabilityEntry = Field(default_factory=RoleCapabilityEntry)


class RoleCapabilitiesRequest(BaseModel):
    """Request body for PUT /api/admin/config/role-capabilities. Same shape as response."""
    guest: Optional[RoleCapabilityEntry] = None
    user: Optional[RoleCapabilityEntry] = None
    admin: Optional[RoleCapabilityEntry] = None


class QueueConfigResponse(BaseModel):
    """Queue strategy and default priorities."""
    queue_strategy: str = Field(description="fifo | priority | round_robin")
    priority_admin: int = Field(default=10, description="Default priority for admin scans")
    priority_user: int = Field(default=5, description="Default priority for user scans")
    priority_guest: int = Field(default=1, description="Default priority for guest scans")


class QueueConfigRequest(BaseModel):
    """Request to update queue config."""
    queue_strategy: Optional[str] = Field(None, description="fifo | priority | round_robin")
    priority_admin: Optional[int] = None
    priority_user: Optional[int] = None
    priority_guest: Optional[int] = None


@router.get("/config", response_model=SystemConfigResponse)
async def get_system_config(
    actor_context: ActorContext = Depends(get_admin_user),
    system_state_repository: SystemStateRepository = Depends(get_system_state_repository_dependency),
) -> SystemConfigResponse:
    """Get current system configuration (admin)."""
    try:
        state = await system_state_repository.get_singleton()
        if not state:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="System state not found")
        config = state.config or {}
        smtp_config = config.get("smtp")
        if smtp_config and "password" in smtp_config:
            smtp_config = smtp_config.copy()
            smtp_config["password"] = "***" if smtp_config.get("password") else ""
        mj = config.get("max_concurrent_jobs") or config.get("max_concurrent_scans")
        try:
            max_jobs = max(1, min(50, int(mj))) if mj is not None else 3
        except (TypeError, ValueError):
            max_jobs = 3
        return SystemConfigResponse(auth_mode=state.auth_mode, max_concurrent_jobs=max_jobs, smtp=smtp_config)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get system config: {str(e)}")


@router.put("/config/worker-jobs", response_model=SystemConfigResponse)
async def update_worker_jobs_config(
    body: WorkerJobsConfigRequest,
    actor_context: ActorContext = Depends(get_admin_user),
    system_state_repository: SystemStateRepository = Depends(get_system_state_repository_dependency),
) -> SystemConfigResponse:
    """Set max concurrent scan jobs for the worker (stored in system config)."""
    try:
        state = await system_state_repository.get_singleton()
        if not state:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="System state not found")
        state.update_config("max_concurrent_jobs", body.max_concurrent_jobs)
        config = state.config or {}
        config.pop("max_concurrent_scans", None)
        config.pop("scanner_timeout", None)
        state.updated_at = datetime.utcnow()
        await system_state_repository.save(state)
        smtp_config = config.get("smtp")
        if smtp_config and "password" in smtp_config:
            smtp_config = smtp_config.copy()
            smtp_config["password"] = "***" if smtp_config.get("password") else ""
        return SystemConfigResponse(auth_mode=state.auth_mode, max_concurrent_jobs=body.max_concurrent_jobs, smtp=smtp_config)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update worker jobs config: {str(e)}",
        )


@router.get("/config/scan-enforcement")
async def get_scan_enforcement_config(
    actor_context: ActorContext = Depends(get_admin_user),
    system_state_repo: SystemStateRepository = Depends(get_system_state_repository_dependency),
) -> Dict[str, Any]:
    """Rate limits, max scan wall time, and submission policies (enforced on scan create)."""
    try:
        state = await system_state_repo.get_singleton()
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="System state not found",
            )
        cfg = state.config or {}
        el = dict(_default_execution_limits())
        el.update(cfg.get("execution_limits") or {})
        pol = dict(_default_policies())
        pol.update(cfg.get("policies") or {})
        return {"execution_limits": el, "policies": pol}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.put("/config/scan-enforcement")
async def put_scan_enforcement_config(
    body: ScanEnforcementUpdate,
    actor_context: ActorContext = Depends(get_admin_user),
    system_state_repo: SystemStateRepository = Depends(get_system_state_repository_dependency),
) -> Dict[str, Any]:
    if body.execution_limits is None and body.policies is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide execution_limits and/or policies",
        )
    try:
        state = await system_state_repo.get_singleton()
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="System state not found",
            )
        config = dict(state.config or {})
        if body.execution_limits is not None:
            merged = dict(_default_execution_limits())
            merged.update(body.execution_limits)
            dur = merged.get("max_scan_duration_seconds")
            if dur is not None:
                try:
                    d = int(dur)
                    if d < 300 or d > 86400:
                        raise ValueError()
                    merged["max_scan_duration_seconds"] = d
                except (TypeError, ValueError):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="max_scan_duration_seconds must be between 300 and 86400",
                    )
            for key in (
                "max_scans_per_hour_global",
                "max_scans_per_hour_per_user",
                "max_scans_per_hour_per_guest_session",
                "max_concurrent_scans_per_user",
                "max_concurrent_scans_per_guest",
            ):
                v = merged.get(key)
                if v is not None:
                    try:
                        iv = int(v)
                        if iv < 1:
                            raise ValueError()
                        merged[key] = iv
                    except (TypeError, ValueError):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"{key} must be a positive integer or null",
                        )
            # initial_scan_delay_seconds: 0 = immediate, or 60–86400 (1 min – 24 h)
            delay = merged.get("initial_scan_delay_seconds")
            if delay is not None:
                try:
                    d = int(delay)
                    if d < 0 or d > 86400:
                        raise ValueError()
                    merged["initial_scan_delay_seconds"] = d
                except (TypeError, ValueError):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="initial_scan_delay_seconds must be between 0 and 86400",
                    )
            config["execution_limits"] = merged
        if body.policies is not None:
            pol = dict(_default_policies())
            pol.update(body.policies)
            if not isinstance(pol.get("blocked_target_patterns"), list):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="blocked_target_patterns must be a list of strings",
                )
            if not isinstance(pol.get("blocked_scan_types"), list):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="blocked_scan_types must be a list of strings",
                )
            pol["blocked_target_patterns"] = [
                str(x).strip() for x in pol["blocked_target_patterns"] if str(x).strip()
            ]
            pol["blocked_scan_types"] = [
                str(x).strip().lower()
                for x in pol["blocked_scan_types"]
                if str(x).strip()
            ]
            pol["require_auth_for_git"] = bool(pol.get("require_auth_for_git"))
            config["policies"] = pol
        state.config = config
        state.updated_at = datetime.utcnow()
        await system_state_repo.save(state)
        state = await system_state_repo.get_singleton()
        cfg = (state.config or {}).get("execution_limits") or {}
        pol = (state.config or {}).get("policies") or {}
        el = dict(_default_execution_limits())
        el.update(cfg)
        pl = dict(_default_policies())
        pl.update(pol)
        return {"execution_limits": el, "policies": pl}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


class ScanDefaultsResponse(BaseModel):
    """Scan form defaults: finding policy path and whether to apply by default."""
    default_finding_policy_path: str = Field(description="Default path for finding policy file (e.g. .scanning/finding-policy.json)")
    finding_policy_apply_by_default: bool = Field(description="If True, scan form pre-fills and sends this path so the policy is applied automatically.")
    scan_profile_guest: str = Field(description="Configured scan profile for guest scans")
    scan_profile_user: str = Field(description="Configured scan profile for signed-in user scans")
    scan_profile_admin: str = Field(description="Configured scan profile for admin scans")
    scan_profile_max_guest: str = Field(description="Maximum allowed scan profile for guests")
    scan_profile_max_user: str = Field(description="Maximum allowed scan profile for signed-in users")
    scan_profile_max_admin: str = Field(description="Maximum allowed scan profile for admins")
    scan_profile_order: List[str] = Field(default_factory=list, description="Profile hierarchy order (low to high)")
    scan_profiles_catalog: List[str] = Field(default_factory=list, description="Available profiles discovered from scanner manifests")


class ScanDefaultsRequest(BaseModel):
    """Request to update scan form defaults."""
    default_finding_policy_path: Optional[str] = Field(None, max_length=500)
    finding_policy_apply_by_default: Optional[bool] = None
    scan_profile_guest: Optional[str] = None
    scan_profile_user: Optional[str] = None
    scan_profile_admin: Optional[str] = None
    scan_profile_max_guest: Optional[str] = None
    scan_profile_max_user: Optional[str] = None
    scan_profile_max_admin: Optional[str] = None
    scan_profile_order: Optional[List[str]] = None


@router.get("/config/scan-defaults", response_model=ScanDefaultsResponse)
async def get_scan_defaults(
    actor_context: ActorContext = Depends(get_admin_user),
    system_state_repo: SystemStateRepository = Depends(get_system_state_repository_dependency),
    scanner_repo: ScannerRepositoryInterface = Depends(get_scanner_repository_dependency),
) -> ScanDefaultsResponse:
    """Get scan form defaults (admin). Used by Execution Settings and by frontend config."""
    try:
        state = await system_state_repo.get_singleton()
        defaults = dict(_default_scan_defaults())
        if state and state.config:
            defaults.update(state.config.get("scan_defaults") or {})
        catalog = await _scan_profile_catalog(scanner_repo)
        if not catalog:
            catalog = ["standard"]
        order = resolve_profile_order(defaults, catalog=catalog)
        profile_guest = normalize_profile_key(defaults.get("scan_profile_guest")) or order[0]
        profile_user = normalize_profile_key(defaults.get("scan_profile_user")) or order[min(1, len(order) - 1)]
        profile_admin = normalize_profile_key(defaults.get("scan_profile_admin")) or order[-1]
        profile_max_guest = normalize_profile_key(defaults.get("scan_profile_max_guest")) or order[0]
        profile_max_user = normalize_profile_key(defaults.get("scan_profile_max_user")) or order[min(1, len(order) - 1)]
        profile_max_admin = normalize_profile_key(defaults.get("scan_profile_max_admin")) or order[-1]
        return ScanDefaultsResponse(
            default_finding_policy_path=defaults.get("default_finding_policy_path", DEFAULT_FINDING_POLICY_PATH),
            finding_policy_apply_by_default=defaults.get("finding_policy_apply_by_default", DEFAULT_FINDING_POLICY_APPLY_BY_DEFAULT),
            scan_profile_guest=profile_guest if profile_guest in catalog else order[0],
            scan_profile_user=profile_user if profile_user in catalog else order[min(1, len(order) - 1)],
            scan_profile_admin=profile_admin if profile_admin in catalog else order[-1],
            scan_profile_max_guest=profile_max_guest if profile_max_guest in catalog else order[0],
            scan_profile_max_user=profile_max_user if profile_max_user in catalog else order[min(1, len(order) - 1)],
            scan_profile_max_admin=profile_max_admin if profile_max_admin in catalog else order[-1],
            scan_profile_order=order,
            scan_profiles_catalog=catalog,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.put("/config/scan-defaults", response_model=ScanDefaultsResponse)
async def put_scan_defaults(
    body: ScanDefaultsRequest,
    actor_context: ActorContext = Depends(get_admin_user),
    system_state_repo: SystemStateRepository = Depends(get_system_state_repository_dependency),
    scanner_repo: ScannerRepositoryInterface = Depends(get_scanner_repository_dependency),
) -> ScanDefaultsResponse:
    """Update scan form defaults (admin)."""
    try:
        state = await system_state_repo.get_singleton()
        if not state:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="System state not found")
        config = dict(state.config or {})
        scan_defaults = dict(config.get("scan_defaults") or _default_scan_defaults())
        catalog = await _scan_profile_catalog(scanner_repo)
        if not catalog:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No scan profiles available from scanner manifests.",
            )
        allowed = set(catalog)
        current_order = resolve_profile_order(scan_defaults, catalog=catalog)
        if body.default_finding_policy_path is not None:
            path = (body.default_finding_policy_path or "").strip() or DEFAULT_FINDING_POLICY_PATH
            scan_defaults["default_finding_policy_path"] = path[:500]
        if body.finding_policy_apply_by_default is not None:
            scan_defaults["finding_policy_apply_by_default"] = body.finding_policy_apply_by_default
        if body.scan_profile_guest is not None:
            scan_defaults["scan_profile_guest"] = _validate_profile_field(body.scan_profile_guest, catalog=catalog, field_name="scan_profile_guest")
        if body.scan_profile_user is not None:
            scan_defaults["scan_profile_user"] = _validate_profile_field(body.scan_profile_user, catalog=catalog, field_name="scan_profile_user")
        if body.scan_profile_admin is not None:
            scan_defaults["scan_profile_admin"] = _validate_profile_field(body.scan_profile_admin, catalog=catalog, field_name="scan_profile_admin")
        if body.scan_profile_max_guest is not None:
            scan_defaults["scan_profile_max_guest"] = _validate_profile_field(body.scan_profile_max_guest, catalog=catalog, field_name="scan_profile_max_guest")
        if body.scan_profile_max_user is not None:
            scan_defaults["scan_profile_max_user"] = _validate_profile_field(body.scan_profile_max_user, catalog=catalog, field_name="scan_profile_max_user")
        if body.scan_profile_max_admin is not None:
            scan_defaults["scan_profile_max_admin"] = _validate_profile_field(body.scan_profile_max_admin, catalog=catalog, field_name="scan_profile_max_admin")
        if body.scan_profile_order is not None:
            new_order: List[str] = []
            seen = set()
            for item in body.scan_profile_order:
                key = _validate_profile_field(item, catalog=catalog, field_name="scan_profile_order")
                if key and key not in seen:
                    seen.add(key)
                    new_order.append(key)
            for c in catalog:
                if c not in seen:
                    new_order.append(c)
            scan_defaults["scan_profile_order"] = new_order
            current_order = new_order
        config["scan_defaults"] = scan_defaults
        state.config = config
        state.updated_at = datetime.utcnow()
        await system_state_repo.save(state)
        order = resolve_profile_order(scan_defaults, catalog=catalog) if current_order else resolve_profile_order(scan_defaults, catalog=catalog)
        return ScanDefaultsResponse(
            default_finding_policy_path=scan_defaults["default_finding_policy_path"],
            finding_policy_apply_by_default=scan_defaults["finding_policy_apply_by_default"],
            scan_profile_guest=normalize_profile_key(scan_defaults.get("scan_profile_guest")) or order[0],
            scan_profile_user=normalize_profile_key(scan_defaults.get("scan_profile_user")) or order[min(1, len(order) - 1)],
            scan_profile_admin=normalize_profile_key(scan_defaults.get("scan_profile_admin")) or order[-1],
            scan_profile_max_guest=normalize_profile_key(scan_defaults.get("scan_profile_max_guest")) or order[0],
            scan_profile_max_user=normalize_profile_key(scan_defaults.get("scan_profile_max_user")) or order[min(1, len(order) - 1)],
            scan_profile_max_admin=normalize_profile_key(scan_defaults.get("scan_profile_max_admin")) or order[-1],
            scan_profile_order=order,
            scan_profiles_catalog=catalog,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/execution/queue-overview")
async def get_execution_queue_overview(
    actor_context: ActorContext = Depends(get_admin_user),
    scan_repo: ScanRepository = Depends(get_scan_repository_dependency),
) -> Dict[str, Any]:
    """
    Pending/running counts, Redis job queue length, running scans, and next pending jobs
    (order: priority desc, created_at asc) with optional duration estimates.
    """
    try:
        from infrastructure.services.queue_service import QueueService

        pending_count = await scan_repo.count_by_statuses(["pending"])
        running_count = await scan_repo.count_by_statuses(["running"])
        running_rows = await scan_repo.get_running_scans(limit=50)
        pending_rows = await scan_repo.get_queue_items(status_filter="pending", limit=20, offset=0)

        redis_len = 0
        try:
            redis_len = int(await QueueService().get_queue_length())
        except Exception:
            pass

        running_out: List[Dict[str, Any]] = [
            {
                "scan_id": s.id,
                "name": s.name or "",
                "target": (s.target_url or "")[:200],
                "priority": s.priority or 0,
                "started_at": isoformat_utc(s.started_at),
            }
            for s in running_rows
        ]

        next_pending: List[Dict[str, Any]] = []
        for i, s in enumerate(pending_rows[:15]):
            est = None
            if s.scanners:
                est = await ScannerDurationService.get_estimated_time(s.scanners)
            next_pending.append(
                {
                    "position": i + 1,
                    "scan_id": s.id,
                    "name": s.name or "",
                    "target": (s.target_url or "")[:200],
                    "priority": s.priority or 0,
                    "created_at": isoformat_utc(s.created_at),
                    "estimated_time_seconds": est,
                }
            )

        return {
            "pending_count": pending_count,
            "running_count": running_count,
            "redis_queue_length": redis_len,
            "running": running_out,
            "next_pending": next_pending,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load execution queue overview: {str(e)}",
        )


@router.get("/system-health")
async def get_admin_system_health(
    actor_context: ActorContext = Depends(get_admin_user),
) -> Dict[str, Any]:
    """Database, Redis, and worker API reachability for admin dashboard."""
    db_h: Dict[str, Any] = {}
    redis_h: Dict[str, Any] = {}
    try:
        db_h = await get_database_health()
    except Exception:
        db_h = {"status": False, "error": "Unavailable"}
    try:
        redis_h = await get_redis_health()
    except Exception:
        redis_h = {"status": False, "error": "Unavailable"}

    worker_url = (os.getenv("WORKER_API_URL") or "http://worker:8081").rstrip("/")
    worker: Dict[str, Any] = {"url": worker_url, "reachable": False}
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{worker_url}/api/scanners/")
            worker["reachable"] = r.status_code < 500
            worker["http_status"] = r.status_code
    except Exception:
        worker["error"] = "Unavailable"

    overall = (
        "healthy"
        if db_h.get("status") and redis_h.get("status") and worker.get("reachable")
        else "degraded"
    )
    return {
        "overall": overall,
        "database": db_h,
        "redis": redis_h,
        "worker": worker,
    }


@router.get("/config/auth", response_model=AuthConfigResponse)
async def get_auth_config(
    actor_context: ActorContext = Depends(get_admin_user),
    system_state_repo: SystemStateRepository = Depends(get_system_state_repository_dependency),
) -> AuthConfigResponse:
    """
    Get auth configuration (who may access, registration).
    Requires admin privileges.
    """
    try:
        state = await system_state_repo.get_singleton()
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="System state not found"
            )
        config = state.config or {}
        auth_cfg = config.get("auth") or {}
        if not isinstance(auth_cfg, dict):
            auth_cfg = {}
        am = state.auth_mode or config.get("AUTH_MODE", "free")
        approval = auth_cfg.get("registration_approval") or "auto"
        if approval not in ("auto", "admin_approval"):
            approval = "auto"
        return AuthConfigResponse(
            auth_mode=am,
            access_mode=auth_cfg.get("access_mode") or ("public" if am == "free" else "private"),
            allow_self_registration=auth_cfg.get("allow_self_registration", False),
            registration_approval=approval,
            require_email_verification=auth_cfg.get("require_email_verification", False),
            bulk_scan_allow_guests=auth_cfg.get("bulk_scan_allow_guests", False),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get auth config: {str(e)}"
        )


@router.put("/config/auth", response_model=AuthConfigResponse)
async def update_auth_config(
    request: Request,
    body: AuthConfigRequest,
    actor_context: ActorContext = Depends(get_admin_user),
    system_state_repo: SystemStateRepository = Depends(get_system_state_repository_dependency),
) -> AuthConfigResponse:
    """
    Update auth configuration.
    Requires admin privileges.
    """
    try:
        state = await system_state_repo.get_singleton()
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="System state not found"
            )
        config = dict(state.config or {})
        if "auth" not in config:
            config["auth"] = {}
        auth_cfg = config["auth"]
        if body.auth_mode is not None:
            state.auth_mode = body.auth_mode
            config["AUTH_MODE"] = body.auth_mode
        if body.access_mode is not None:
            auth_cfg["access_mode"] = body.access_mode
        if body.allow_self_registration is not None:
            auth_cfg["allow_self_registration"] = body.allow_self_registration
        if body.registration_approval is not None:
            if body.registration_approval not in ("auto", "admin_approval"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="registration_approval must be 'auto' or 'admin_approval'",
                )
            auth_cfg["registration_approval"] = body.registration_approval
        if body.require_email_verification is not None:
            auth_cfg["require_email_verification"] = body.require_email_verification
        if body.bulk_scan_allow_guests is not None:
            auth_cfg["bulk_scan_allow_guests"] = body.bulk_scan_allow_guests
        config["auth"] = auth_cfg
        state.config = config
        state.updated_at = datetime.utcnow()
        await system_state_repo.save(state)
        from config.settings import load_settings_from_database, settings as app_settings
        await load_settings_from_database(app_settings)
        await AuditLogService.log_event(
            user_id=actor_context.user_id,
            user_email=actor_context.email,
            action_type="AUTH_CONFIG_CHANGED",
            target="auth_config",
            details={"access_mode": auth_cfg.get("access_mode"), "allow_self_registration": auth_cfg.get("allow_self_registration"), "registration_approval": auth_cfg.get("registration_approval"), "require_email_verification": auth_cfg.get("require_email_verification"), "bulk_scan_allow_guests": auth_cfg.get("bulk_scan_allow_guests"), "auth_mode": state.auth_mode},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent")
        )
        approval = auth_cfg.get("registration_approval") or "auto"
        return AuthConfigResponse(
            auth_mode=state.auth_mode,
            access_mode=auth_cfg.get("access_mode") or ("public" if state.auth_mode == "free" else "private"),
            allow_self_registration=auth_cfg.get("allow_self_registration", False),
            registration_approval=approval,
            require_email_verification=auth_cfg.get("require_email_verification", False),
            bulk_scan_allow_guests=auth_cfg.get("bulk_scan_allow_guests", False),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update auth config: {str(e)}"
        )


def _role_capability_entry_from_dict(data: Any) -> RoleCapabilityEntry:
    """Build RoleCapabilityEntry from stored dict (with defaults for missing keys)."""
    if not isinstance(data, dict):
        return RoleCapabilityEntry()
    return RoleCapabilityEntry(
        allowed_target_types=list(data.get("allowed_target_types") or []),
        allowed_scanner_tools_keys=list(data.get("allowed_scanner_tools_keys") or []),
        my_targets_allowed=bool(data.get("my_targets_allowed", False)),
        my_targets_target_types=data.get("my_targets_target_types"),
    )


def _validate_role_capability_entry(entry: RoleCapabilityEntry, role_name: str) -> None:
    """Validate allowed_target_types and my_targets_target_types against ROLE_CAPABILITY_TARGET_TYPES."""
    invalid = [t for t in entry.allowed_target_types if t not in ROLE_CAPABILITY_TARGET_TYPES]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"role_capabilities.{role_name}.allowed_target_types: invalid types: {invalid}. Valid: {sorted(ROLE_CAPABILITY_TARGET_TYPES)}",
        )
    if entry.my_targets_target_types is not None:
        invalid_mt = [t for t in entry.my_targets_target_types if t not in ROLE_CAPABILITY_TARGET_TYPES]
        if invalid_mt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"role_capabilities.{role_name}.my_targets_target_types: invalid types: {invalid_mt}. Valid: {sorted(ROLE_CAPABILITY_TARGET_TYPES)}",
            )


@router.get("/config/role-capabilities", response_model=RoleCapabilitiesResponse)
async def get_role_capabilities(
    actor_context: ActorContext = Depends(get_admin_user),
    system_state_repo: SystemStateRepository = Depends(get_system_state_repository_dependency),
) -> RoleCapabilitiesResponse:
    """
    Get role capabilities (allowed target types, scanners, My Targets per role).
    Stored in SystemState.config["role_capabilities"]. Returns defaults for missing keys.
    Requires admin privileges.
    """
    try:
        state = await system_state_repo.get_singleton()
        if not state:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="System state not found")
        config = state.config or {}
        merged_by_role = merge_role_capabilities_raw(config)
        out = {role: _role_capability_entry_from_dict(merged_by_role[role]) for role in ROLE_NAMES}
        return RoleCapabilitiesResponse(**out)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get role capabilities: {str(e)}",
        )


@router.put("/config/role-capabilities", response_model=RoleCapabilitiesResponse)
async def update_role_capabilities(
    request: Request,
    body: RoleCapabilitiesRequest,
    actor_context: ActorContext = Depends(get_admin_user),
    system_state_repo: SystemStateRepository = Depends(get_system_state_repository_dependency),
) -> RoleCapabilitiesResponse:
    """
    Update role capabilities. Partial update: only provided roles are updated; others unchanged.
    Requires admin privileges.
    """
    try:
        state = await system_state_repo.get_singleton()
        if not state:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="System state not found")
        config = dict(state.config or {})
        raw = config.get("role_capabilities") or {}
        if not isinstance(raw, dict):
            raw = {}
        defaults = default_role_capabilities()
        # Merge current + defaults so we have full entries, then apply body
        for role in ROLE_NAMES:
            current = {**(defaults.get(role) or {}), **(raw.get(role) or {})}
            entry = body.guest if role == "guest" else (body.user if role == "user" else body.admin)
            if entry is not None:
                _validate_role_capability_entry(entry, role)
                raw[role] = {
                    "allowed_target_types": entry.allowed_target_types,
                    "allowed_scanner_tools_keys": entry.allowed_scanner_tools_keys,
                    "my_targets_allowed": entry.my_targets_allowed,
                    "my_targets_target_types": entry.my_targets_target_types,
                }
            else:
                raw[role] = current
        config["role_capabilities"] = raw
        state.config = config
        state.updated_at = datetime.utcnow()
        await system_state_repo.save(state)
        await AuditLogService.log_event(
            user_id=actor_context.user_id,
            user_email=actor_context.email,
            action_type="ROLE_CAPABILITIES_CHANGED",
            target="role_capabilities",
            details={"roles_updated": [r for r in ROLE_NAMES if getattr(body, r) is not None]},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
        )
        out = {}
        for role in ROLE_NAMES:
            out[role] = _role_capability_entry_from_dict(raw.get(role) or {})
        return RoleCapabilitiesResponse(**out)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update role capabilities: {str(e)}",
        )


@router.get("/config/queue", response_model=QueueConfigResponse)
async def get_queue_config(
    actor_context: ActorContext = Depends(get_admin_user),
    system_state_repo: SystemStateRepository = Depends(get_system_state_repository_dependency),
) -> QueueConfigResponse:
    """Get queue strategy and priority defaults. Requires admin."""
    try:
        state = await system_state_repo.get_singleton()
        if not state:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="System state not found")
        config = state.config or {}
        queue_cfg = config.get("queue") or {}
        from config.settings import get_settings
        s = get_settings()
        return QueueConfigResponse(
            queue_strategy=queue_cfg.get("queue_strategy") or getattr(s, "QUEUE_STRATEGY", "fifo"),
            priority_admin=int(queue_cfg.get("priority_admin", getattr(s, "QUEUE_PRIORITY_ADMIN", 10))),
            priority_user=int(queue_cfg.get("priority_user", getattr(s, "QUEUE_PRIORITY_USER", 5))),
            priority_guest=int(queue_cfg.get("priority_guest", getattr(s, "QUEUE_PRIORITY_GUEST", 1))),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/config/queue", response_model=QueueConfigResponse)
async def update_queue_config(
    body: QueueConfigRequest,
    actor_context: ActorContext = Depends(get_admin_user),
    system_state_repo: SystemStateRepository = Depends(get_system_state_repository_dependency),
) -> QueueConfigResponse:
    """Update queue strategy and priority defaults. Requires admin."""
    try:
        state = await system_state_repo.get_singleton()
        if not state:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="System state not found")
        config = dict(state.config or {})
        if "queue" not in config:
            config["queue"] = {}
        q = config["queue"]
        if body.queue_strategy is not None and body.queue_strategy in ("fifo", "priority", "round_robin"):
            q["queue_strategy"] = body.queue_strategy
        if body.priority_admin is not None:
            q["priority_admin"] = body.priority_admin
        if body.priority_user is not None:
            q["priority_user"] = body.priority_user
        if body.priority_guest is not None:
            q["priority_guest"] = body.priority_guest
        state.config = config
        state.updated_at = datetime.utcnow()
        await system_state_repo.save(state)
        from config.settings import load_settings_from_database, get_settings
        await load_settings_from_database(get_settings())
        return QueueConfigResponse(
            queue_strategy=q.get("queue_strategy", "fifo"),
            priority_admin=int(q.get("priority_admin", 10)),
            priority_user=int(q.get("priority_user", 5)),
            priority_guest=int(q.get("priority_guest", 1)),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/config/smtp", response_model=SMTPConfigResponse)
async def update_smtp_config(
    smtp_config: SMTPConfigRequest,
    actor_context: ActorContext = Depends(get_admin_user),
    system_state_repo: SystemStateRepository = Depends(get_system_state_repository_dependency),
) -> SMTPConfigResponse:
    """
    Update SMTP configuration.
    
    Requires admin privileges.
    Note: Changes require service restart to take effect.
    """
    try:
        state = await system_state_repo.get_singleton()
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="System state not found"
            )
        config = dict(state.config or {})
        config["smtp"] = {
            "enabled": smtp_config.enabled,
            "host": smtp_config.host,
            "port": smtp_config.port,
            "user": smtp_config.user,
            "password": smtp_config.password,
            "use_tls": smtp_config.use_tls,
            "from_email": smtp_config.from_email,
            "from_name": smtp_config.from_name
        }
        state.config = config
        state.updated_at = datetime.utcnow()
        await system_state_repo.save(state)
        return SMTPConfigResponse(
            enabled=smtp_config.enabled,
            host=smtp_config.host,
            port=smtp_config.port,
            user=smtp_config.user,
            password="***" if smtp_config.password else "",
            use_tls=smtp_config.use_tls,
            from_email=smtp_config.from_email,
            from_name=smtp_config.from_name
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update SMTP config: {str(e)}"
        )


@router.get("/config/smtp", response_model=SMTPConfigResponse)
async def get_smtp_config(
    actor_context: ActorContext = Depends(get_admin_user),
    system_state_repo: SystemStateRepository = Depends(get_system_state_repository_dependency),
) -> SMTPConfigResponse:
    """
    Get current SMTP configuration.
    
    Requires admin privileges.
    """
    try:
        state = await system_state_repo.get_singleton()
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="System state not found"
            )
        config = state.config or {}
        smtp_config = config.get("smtp", {})
        return SMTPConfigResponse(
            enabled=smtp_config.get("enabled", False),
            host=smtp_config.get("host", "smtp.gmail.com"),
            port=smtp_config.get("port", 587),
            user=smtp_config.get("user", ""),
            password="***" if smtp_config.get("password") else "",
            use_tls=smtp_config.get("use_tls", True),
            from_email=smtp_config.get("from_email", "noreply@simpleseccheck.local"),
            from_name=smtp_config.get("from_name", "SimpleSecCheck")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get SMTP config: {str(e)}"
        )


# ============================================================================
# Audit Log Endpoints
# ============================================================================

@router.get("/audit-log")
async def get_audit_log(
    request: Request,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user_id: Optional[str] = Query(None),
    action_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    actor_context: ActorContext = Depends(get_admin_user),
) -> Dict[str, Any]:
    """
    Get audit log entries with filtering and pagination.
    
    Requires admin privileges.
    """
    try:
        # Parse dates
        start_dt = None
        end_dt = None
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        result = await AuditLogService.get_audit_log(
            limit=limit,
            offset=offset,
            user_id=user_id,
            action_type=action_type,
            start_date=start_dt,
            end_date=end_dt,
            search=search
        )
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get audit log: {str(e)}"
        )


@router.post("/audit-log/export")
async def export_audit_log(
    request: Request,
    format: str = Query("json", pattern="^(json|csv)$"),
    user_id: Optional[str] = Query(None),
    action_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    actor_context: ActorContext = Depends(get_admin_user),
):
    """
    Export audit log in specified format (JSON or CSV).
    
    Requires admin privileges.
    """
    try:
        # Parse dates
        start_dt = None
        end_dt = None
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        data = await AuditLogService.export_audit_log(
            format=format,
            user_id=user_id,
            action_type=action_type,
            start_date=start_dt,
            end_date=end_dt
        )
        
        from fastapi.responses import Response
        
        if format == "csv":
            return Response(
                content=data,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=audit_log_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"}
            )
        else:
            return Response(
                content=data,
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=audit_log_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"}
            )
    except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to export audit log: {str(e)}"
            )


# ============================================================================
# User Management Endpoints
# ============================================================================

class UserCreateRequest(BaseModel):
    """Request for creating a new user."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    role: str = Field(default="user", pattern="^(admin|user)$")


class UserUpdateRequest(BaseModel):
    """Request for updating a user."""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    role: Optional[str] = Field(None, pattern="^(admin|user)$")
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """Response for user information."""
    id: str
    email: str
    username: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: str
    last_login: Optional[str] = None


class GuestSessionItem(BaseModel):
    """Guest browser session (session_id cookie), tracked in Redis."""

    session_id: str
    created_at: Optional[str] = Field(None, description="ISO UTC from issued timestamp")
    expires_at: Optional[str] = Field(None, description="ISO UTC (issued + 30d)")
    revoked: bool = False


class GuestSessionListResponse(BaseModel):
    items: List[GuestSessionItem]
    truncated: bool = Field(False, description="True if more keys exist than returned")


@router.get("/guest-sessions", response_model=GuestSessionListResponse)
async def list_guest_sessions(
    request: Request,
    limit: int = Query(200, ge=1, le=1000),
    actor_context: ActorContext = Depends(get_admin_user),
) -> GuestSessionListResponse:
    """
    List guest sessions currently tracked in Redis (issued, not yet expired TTL).
    Revoked sessions may still appear until issued key expires unless deleted.
    """
    from infrastructure.redis.client import redis_client
    from infrastructure.redis.guest_session_keys import (
        issued_key,
        revoked_key,
        TTL_SECONDS,
    )

    try:
        keys = await redis_client.scan_keys("guest:session:issued:*", limit + 1)
        truncated = len(keys) > limit
        keys = keys[:limit]
        items: List[GuestSessionItem] = []
        prefix = "guest:session:issued:"
        for k in keys:
            if not k.startswith(prefix):
                continue
            sid = k[len(prefix) :]
            try:
                UUID(sid)
            except ValueError:
                continue
            issued_raw = await redis_client.get(issued_key(sid))
            revoked = bool(await redis_client.get(revoked_key(sid)))
            created_at = None
            expires_at = None
            if issued_raw:
                try:
                    ts = int(issued_raw)
                    created_at = datetime.utcfromtimestamp(ts).isoformat() + "Z"
                    expires_at = (
                        datetime.utcfromtimestamp(ts + TTL_SECONDS).isoformat() + "Z"
                    )
                except (TypeError, ValueError):
                    pass
            items.append(
                GuestSessionItem(
                    session_id=sid,
                    created_at=created_at,
                    expires_at=expires_at,
                    revoked=revoked,
                )
            )
        await AuditLogService.log_event(
            user_id=actor_context.user_id,
            user_email=actor_context.email,
            action_type="GUEST_SESSION_LIST_VIEWED",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
        )
        return GuestSessionListResponse(items=items, truncated=truncated)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list guest sessions: {str(e)}",
        )


@router.get("/guest-sessions/{session_id}", response_model=GuestSessionItem)
async def get_guest_session(
    session_id: str,
    actor_context: ActorContext = Depends(get_admin_user),
) -> GuestSessionItem:
    """Inspect one guest session (Redis issued / revoked)."""
    from infrastructure.redis.client import redis_client
    from infrastructure.redis.guest_session_keys import (
        issued_key,
        revoked_key,
        TTL_SECONDS,
    )

    try:
        try:
            UUID(session_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="session_id must be a UUID",
            )
        issued_raw = await redis_client.get(issued_key(session_id))
        revoked = bool(await redis_client.get(revoked_key(session_id)))
        created_at = None
        expires_at = None
        if issued_raw:
            try:
                ts = int(issued_raw)
                created_at = datetime.utcfromtimestamp(ts).isoformat() + "Z"
                expires_at = (
                    datetime.utcfromtimestamp(ts + TTL_SECONDS).isoformat() + "Z"
                )
            except (TypeError, ValueError):
                pass
        return GuestSessionItem(
            session_id=session_id,
            created_at=created_at,
            expires_at=expires_at,
            revoked=revoked,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get guest session: {str(e)}",
        )


class GuestSessionRevokeResponse(BaseModel):
    message: str
    session_id: str


@router.delete("/guest-sessions/{session_id}", response_model=GuestSessionRevokeResponse)
async def revoke_guest_session(
    request: Request,
    session_id: str,
    actor_context: ActorContext = Depends(get_admin_user),
) -> GuestSessionRevokeResponse:
    """
    Revoke a guest session: the browser cookie becomes useless; next request gets a new guest session.
    """
    from infrastructure.redis.client import redis_client
    from infrastructure.redis.guest_session_keys import revoked_key, TTL_SECONDS

    try:
        try:
            UUID(session_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="session_id must be a UUID",
            )
        await redis_client.set(
            revoked_key(session_id), "1", expire=TTL_SECONDS
        )
        await AuditLogService.log_event(
            user_id=actor_context.user_id,
            user_email=actor_context.email,
            action_type="GUEST_SESSION_REVOKED",
            target=session_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
        )
        return GuestSessionRevokeResponse(
            message="Guest session revoked. Client will receive a new session on next request.",
            session_id=session_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke guest session: {str(e)}",
        )


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    request: Request,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None, description="Filter: all (default), active, pending (awaiting admin approval)"),
    actor_context: ActorContext = Depends(get_admin_user),
    user_service: UserService = Depends(lambda: get_user_service()),
) -> List[UserResponse]:
    """
    List users with pagination. Use status=pending to list users awaiting admin approval.
    
    Requires admin privileges.
    """
    try:
        active_only = None
        if status == "active":
            active_only = True
        elif status == "pending":
            active_only = False
        users = await user_service.list_all(limit=limit, offset=offset, active_only=active_only)
        await AuditLogService.log_event(
            user_id=actor_context.user_id,
            user_email=actor_context.email,
            action_type="USER_LIST_VIEWED",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent")
        )
        return [
            UserResponse(
                id=u.id,
                email=u.email,
                username=u.username,
                role=u.role.value,
                is_active=u.is_active,
                is_verified=u.is_verified,
                created_at=isoformat_utc(u.created_at),
                last_login=isoformat_utc(u.last_login),
            )
            for u in users
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list users: {str(e)}"
        )


@router.post("/users", response_model=UserResponse)
async def create_user(
    request: Request,
    user_data: UserCreateRequest,
    actor_context: ActorContext = Depends(get_admin_user),
    user_service: UserService = Depends(lambda: get_user_service()),
) -> UserResponse:
    """
    Create a new user.
    
    Requires admin privileges.
    """
    try:
        from api.services.password_service import PasswordService
        from domain.entities.user import User, UserRole

        if await user_service.get_by_email(user_data.email, active_only=False) or await user_service.get_by_username(user_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email or username already exists"
            )
        password_service = PasswordService()
        password_hash = password_service.hash_password(user_data.password)
        role = UserRole.ADMIN if user_data.role == "admin" else UserRole.USER
        new_user = User(
            email=user_data.email,
            username=user_data.username,
            password_hash=password_hash,
            role=role,
            is_active=True,
            is_verified=False,
        )
        new_user = await user_service.create(new_user)
        await AuditLogService.log_event(
            user_id=actor_context.user_id,
            user_email=actor_context.email,
            action_type="USER_CREATED",
            target=user_data.email,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent")
        )
        return UserResponse(
            id=new_user.id,
            email=new_user.email,
            username=new_user.username,
            role=new_user.role.value,
            is_active=new_user.is_active,
            is_verified=new_user.is_verified,
            created_at=isoformat_utc(new_user.created_at),
            last_login=None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    request: Request,
    user_id: str,
    user_data: UserUpdateRequest,
    actor_context: ActorContext = Depends(get_admin_user),
    user_service: UserService = Depends(lambda: get_user_service()),
) -> UserResponse:
    """
    Update a user.
    
    Requires admin privileges.
    """
    try:
        from domain.entities.user import UserRole

        user = await user_service.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        if user_data.email is not None:
            user.email = user_data.email
        if user_data.username is not None:
            user.username = user_data.username
        if user_data.role is not None:
            user.role = UserRole.ADMIN if user_data.role == "admin" else UserRole.USER
        if user_data.is_active is not None:
            user.is_active = user_data.is_active
        user.updated_at = datetime.utcnow()
        user = await user_service.update(user)
        await AuditLogService.log_event(
            user_id=actor_context.user_id,
            user_email=actor_context.email,
            action_type="USER_UPDATED",
            target=user.email,
            details={"changes": user_data.dict(exclude_unset=True)},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent")
        )
        return UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            role=user.role.value,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=isoformat_utc(user.created_at),
            last_login=isoformat_utc(user.last_login),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )


@router.delete("/users/{user_id}")
async def delete_user(
    request: Request,
    user_id: str,
    actor_context: ActorContext = Depends(get_admin_user),
    user_service: UserService = Depends(lambda: get_user_service()),
) -> Dict[str, str]:
    """
    Delete a user.
    
    Requires admin privileges.
    """
    try:
        user = await user_service.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        user_email = user.email
        await user_service.delete_by_id(user_id)
        await AuditLogService.log_event(
            user_id=actor_context.user_id,
            user_email=actor_context.email,
            action_type="USER_DELETED",
            target=user_email,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent")
        )
        return {"message": "User deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )


# ============================================================================
# Feature Flags Endpoints
# ============================================================================

@router.get("/feature-flags")
async def get_feature_flags(
    actor_context: ActorContext = Depends(get_admin_user),
    system_state_repo: SystemStateRepository = Depends(get_system_state_repository_dependency),
) -> Dict[str, Any]:
    """
    Get current feature flags.
    
    Requires admin privileges.
    """
    try:
        state = await system_state_repo.get_singleton()
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="System state not found"
            )
        config = state.config or {}
        feature_flags = config.get("feature_flags", {})
        return {key: feature_flags.get(key, True) for key in ALL_SCAN_FEATURE_FLAG_KEYS}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get feature flags: {str(e)}"
        )


@router.put("/feature-flags")
async def update_feature_flags(
    request: Request,
    feature_flags: Dict[str, bool],
    actor_context: ActorContext = Depends(get_admin_user),
    system_state_repo: SystemStateRepository = Depends(get_system_state_repository_dependency),
) -> Dict[str, Any]:
    """
    Update feature flags.
    
    Requires admin privileges.
    """
    try:
        state = await system_state_repo.get_singleton()
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="System state not found"
            )
        config = dict(state.config or {})
        if "feature_flags" not in config:
            config["feature_flags"] = {}
        allowed = {k: bool(v) for k, v in feature_flags.items() if k in ALL_SCAN_FEATURE_FLAG_KEYS}
        old_flags = config["feature_flags"].copy()
        config["feature_flags"].update(allowed)
        state.config = config
        state.updated_at = datetime.utcnow()
        await system_state_repo.save(state)
        changes = {k: v for k, v in allowed.items() if old_flags.get(k) != v}
        await AuditLogService.log_event(
            user_id=actor_context.user_id,
            user_email=actor_context.email,
            action_type="FEATURE_FLAG_CHANGED",
            target="feature_flags",
            details={"changes": changes},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent")
        )
        return {key: config["feature_flags"].get(key, True) for key in ALL_SCAN_FEATURE_FLAG_KEYS}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update feature flags: {str(e)}"
        )


# ============================================================================
# IP & Abuse Protection Endpoints
# ============================================================================

class BlockIPRequest(BaseModel):
    """Request for blocking an IP address."""
    ip_address: str = Field(..., description="IP address to block")
    reason: str = Field(default="manual", description="Reason for blocking")
    expires_at: Optional[str] = Field(None, description="Expiration date (ISO format), null for permanent")


class IPControlResponse(BaseModel):
    """Response for IP control dashboard."""
    blocked_ips: List[Dict[str, Any]]
    suspicious_activity: List[Dict[str, Any]]
    statistics: Dict[str, Any]


@router.get("/security/ip-control", response_model=IPControlResponse)
async def get_ip_control(
    actor_context: ActorContext = Depends(get_admin_user),
    blocked_ip_repo: BlockedIPRepository = Depends(lambda: get_blocked_ip_repository()),
) -> IPControlResponse:
    """
    Get IP control dashboard data.
    
    Requires admin privileges.
    """
    try:
        from datetime import timedelta

        since = datetime.utcnow() - timedelta(hours=24)
        blocked_list = await blocked_ip_repo.list_all(active_only=True)
        suspicious = await blocked_ip_repo.get_activity_stats(since=since, limit=50)
        stats = await blocked_ip_repo.get_stats(activity_since=since)
        return IPControlResponse(
            blocked_ips=[
                {
                    "id": ip.id,
                    "ip_address": ip.ip_address,
                    "reason": ip.reason,
                    "blocked_at": isoformat_utc(ip.blocked_at),
                    "expires_at": isoformat_utc(ip.expires_at),
                }
                for ip in blocked_list
            ],
            suspicious_activity=suspicious,
            statistics={
                "total_blocked": stats["total_blocked"],
                "total_activity_24h": stats["total_activity_24h"]
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get IP control data: {str(e)}"
        )


@router.post("/security/ip-control/block")
async def block_ip(
    request: Request,
    block_data: BlockIPRequest,
    actor_context: ActorContext = Depends(get_admin_user),
    blocked_ip_repo: BlockedIPRepository = Depends(lambda: get_blocked_ip_repository()),
) -> Dict[str, str]:
    """
    Block an IP address.
    
    Requires admin privileges.
    """
    try:
        from ipaddress import ip_address as validate_ip

        try:
            validate_ip(block_data.ip_address)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid IP address"
            )
        expires_at = None
        if block_data.expires_at:
            expires_at = datetime.fromisoformat(block_data.expires_at.replace('Z', '+00:00'))
        existing = await blocked_ip_repo.get_by_ip(block_data.ip_address)
        if existing:
            existing.reason = block_data.reason
            existing.expires_at = expires_at
            existing.is_active = True
            existing.blocked_at = datetime.utcnow()
            await blocked_ip_repo.update(existing)
        else:
            await blocked_ip_repo.create(
                ip_address=block_data.ip_address,
                reason=block_data.reason,
                blocked_by=actor_context.user_id,
                expires_at=expires_at,
            )
        await AuditLogService.log_event(
            user_id=actor_context.user_id,
            user_email=actor_context.email,
            action_type="IP_BLOCKED",
            target=block_data.ip_address,
            details={"reason": block_data.reason, "expires_at": block_data.expires_at},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent")
        )
        return {"message": f"IP {block_data.ip_address} blocked successfully"}
    except HTTPException:
        raise
    except ValueError as e:
        if "already blocked" in str(e).lower():
            await AuditLogService.log_event(
                user_id=actor_context.user_id,
                user_email=actor_context.email,
                action_type="IP_BLOCKED",
                target=block_data.ip_address,
                details={"reason": block_data.reason},
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent")
            )
            return {"message": f"IP {block_data.ip_address} blocked successfully"}
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to block IP: {str(e)}"
        )


@router.post("/security/ip-control/unblock")
async def unblock_ip(
    request: Request,
    ip_address: str = Query(..., description="IP address to unblock"),
    actor_context: ActorContext = Depends(get_admin_user),
    blocked_ip_repo: BlockedIPRepository = Depends(lambda: get_blocked_ip_repository()),
) -> Dict[str, str]:
    """
    Unblock an IP address.
    
    Requires admin privileges.
    """
    try:
        removed = await blocked_ip_repo.delete_by_ip(ip_address)
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="IP address not found in blocked list"
            )
        await AuditLogService.log_event(
            user_id=actor_context.user_id,
            user_email=actor_context.email,
            action_type="IP_UNBLOCKED",
            target=ip_address,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent")
        )
        return {"message": f"IP {ip_address} unblocked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unblock IP: {str(e)}"
        )


# ============================================================================
# Scan Engine Management Endpoints
# ============================================================================

class ScannerStatusResponse(BaseModel):
    """Response for scanner engine status."""
    workers_running: int
    queue_size: int
    active_scans: int
    average_scan_time: Optional[float] = None
    timeouts_today: int
    errors_today: int
    scans_completed_today: int
    queue_items: List[Dict[str, Any]] = []


@router.get("/scanner", response_model=ScannerStatusResponse)
async def get_scanner_status(
    actor_context: ActorContext = Depends(get_admin_user),
    scan_repo: ScanRepository = Depends(get_scan_repository_dependency),
) -> ScannerStatusResponse:
    """
    Get scan engine status and metrics.
    
    Requires admin privileges.
    """
    try:
        from infrastructure.services.queue_service import QueueService

        queue_service = QueueService()
        queue_size = await queue_service.get_queue_length()
        active_scans = await scan_repo.count_by_statuses(["running"])
        timeouts_today = await scan_repo.count_today_by_filters(error_message_contains="timeout")
        errors_today = await scan_repo.count_today_by_filters(status="failed")
        scans_completed_today = await scan_repo.count_today_by_filters(status="completed")
        avg_scan_time = await scan_repo.get_avg_duration_completed_today()
        pending = await scan_repo.get_queue_items(status_filter="pending", limit=10, offset=0)
        queue_items = [
            {
                "scan_id": s.id,
                "name": s.name,
                "target": s.target_url,
                "created_at": isoformat_utc(s.created_at),
                "priority": s.priority
            }
            for s in pending
        ]
        workers_running = max(1, active_scans)
        return ScannerStatusResponse(
            workers_running=workers_running,
            queue_size=queue_size,
            active_scans=active_scans,
            average_scan_time=float(avg_scan_time) if avg_scan_time else None,
            timeouts_today=timeouts_today,
            errors_today=errors_today,
            scans_completed_today=scans_completed_today,
            queue_items=queue_items
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scanner status: {str(e)}"
        )


@router.post("/scanner/pause")
async def pause_scanning(
    request: Request,
    actor_context: ActorContext = Depends(get_admin_user),
) -> Dict[str, str]:
    """
    Pause scanning (stop processing new scans).
    
    Requires admin privileges.
    Note: This is a placeholder - actual implementation would require worker coordination.
    """
    try:
        # Log audit event
        await AuditLogService.log_event(
            user_id=actor_context.user_id,
            user_email=actor_context.email,
            action_type="SCANNER_PAUSED",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent")
        )
        
        # TODO: Implement actual pause logic (would need worker API call)
        return {"message": "Scanning paused (placeholder - not yet implemented)"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pause scanning: {str(e)}"
        )


@router.post("/scanner/resume")
async def resume_scanning(
    request: Request,
    actor_context: ActorContext = Depends(get_admin_user),
) -> Dict[str, str]:
    """
    Resume scanning (start processing new scans).
    
    Requires admin privileges.
    Note: This is a placeholder - actual implementation would require worker coordination.
    """
    try:
        # Log audit event
        await AuditLogService.log_event(
            user_id=actor_context.user_id,
            user_email=actor_context.email,
            action_type="SCANNER_RESUMED",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent")
        )
        
        # TODO: Implement actual resume logic (would need worker API call)
        return {"message": "Scanning resumed (placeholder - not yet implemented)"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume scanning: {str(e)}"
        )


@router.get("/scanner-duration-stats")
async def get_scanner_duration_stats(
    actor_context: ActorContext = Depends(get_admin_user),
) -> Dict[str, Any]:
    """
    Get exact duration statistics per scanner/tool (admin only).
    Used for queue estimates; only real data, no fake defaults.
    """
    try:
        stats = await ScannerDurationService.get_all_stats()
        return {"scanner_duration_stats": stats}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scanner duration stats: {str(e)}"
        )


def _mask_sensitive_config(config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not config:
        return {}
    out = {}
    for k, v in config.items():
        ku = str(k).upper()
        if any(x in ku for x in ("TOKEN", "PASSWORD", "SECRET", "KEY", "AUTH")) and v:
            out[k] = "********"
        else:
            out[k] = v
    return out


def _merge_tool_config(old: Optional[Dict], new: Optional[Dict]) -> Dict[str, Any]:
    old = dict(old or {})
    if not new:
        return old
    sens = ("TOKEN", "PASSWORD", "SECRET", "KEY", "AUTH")
    for k, v in new.items():
        if v is None:
            continue
        vs = str(v).strip()
        if vs in ("", "********") and any(x in str(k).upper() for x in sens):
            continue
        if vs == "":
            old.pop(k, None)
        else:
            old[k] = v
    return old


class ScannerToolSettingsPut(BaseModel):
    """DB override layer; null = do not change column (use omit for clear)."""

    enabled: Optional[bool] = Field(None, description="false = force disable tool; true = force enable; omit/null = use discovery")
    timeout_seconds: Optional[int] = Field(None, ge=30, le=86400, description="Override manifest timeout")
    config: Optional[Dict[str, Any]] = Field(
        None,
        description="Env vars per scanner run e.g. SONAR_HOST_URL, SONAR_TOKEN, SNYK_TOKEN",
    )


def _tools_key_from_scanner_entity(sc) -> Optional[str]:
    tk = (sc.scanner_metadata or {}).get("tools_key")
    return str(tk).strip() if tk else None


@router.get("/scanner-tool-settings")
async def get_scanner_tool_settings(
    actor_context: ActorContext = Depends(get_admin_user),
    scanner_repo: ScannerRepositoryInterface = Depends(lambda: get_scanner_repository()),
    settings_repo: ScannerToolSettingsRepository = Depends(lambda: get_scanner_tool_settings_repository()),
) -> Dict[str, Any]:
    """
    List scanners. DB overrides are keyed by tools_key (slug), not display name.
    """
    from application.services.scanner_tool_overrides_service import standard_profile_timeout_from_meta

    scanners = await scanner_repo.list_all()
    settings_list = await settings_repo.list_all()
    db_map = {s.scanner_key: s for s in settings_list}
    items = []
    for sc in scanners:
        tk = _tools_key_from_scanner_entity(sc)
        if not tk:
            continue
        meta = sc.scanner_metadata or {}
        mt = standard_profile_timeout_from_meta(meta)
        row = db_map.get(tk)
        if row and row.timeout_seconds is not None and row.timeout_seconds > 0:
            eff_timeout = int(row.timeout_seconds)
        else:
            eff_timeout = mt
        eff_enabled = row.enabled if row is not None and row.enabled is not None else sc.enabled
        items.append(
            {
                "tools_key": tk,
                "display_name": sc.name,
                "standard_profile_timeout": mt,
                "discovery_enabled": sc.enabled,
                "effective_timeout": eff_timeout,
                "effective_enabled": eff_enabled,
                "db_override": {
                    "enabled": row.enabled if row else None,
                    "timeout_seconds": row.timeout_seconds if row else None,
                    "config": _mask_sensitive_config(row.config if row else {}),
                }
                if row
                else None,
            }
        )
    return {
        "scanners": items,
        "help": {
            "tools_key": "Use slug in API path (e.g. sonarqube, semgrep). From scanner sync metadata.",
            "config_examples": {"sonarqube": ["SONAR_HOST_URL", "SONAR_TOKEN"], "snyk": ["SNYK_TOKEN"]},
        },
    }


@router.put("/scanner-tool-settings/{tools_key:path}")
async def put_scanner_tool_settings(
    tools_key: str,
    body: ScannerToolSettingsPut,
    request: Request,
    actor_context: ActorContext = Depends(get_admin_user),
    scanner_repo: ScannerRepositoryInterface = Depends(lambda: get_scanner_repository()),
    settings_repo: ScannerToolSettingsRepository = Depends(lambda: get_scanner_tool_settings_repository()),
) -> Dict[str, Any]:
    sc = await scanner_repo.get_by_tools_key(tools_key)
    if not sc:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown tools_key: {tools_key}. Sync scanners first; use slug e.g. semgrep, sonarqube.",
        )
    tk = _tools_key_from_scanner_entity(sc)
    if not tk:
        raise HTTPException(status_code=404, detail=f"Scanner has no tools_key: {tools_key}")
    uid = actor_context.user_id
    row = await settings_repo.get_by_key(tk)
    if row is None:
        if body.enabled is None and body.timeout_seconds is None and body.config is None:
            raise HTTPException(
                status_code=400,
                detail="Provide at least one of enabled, timeout_seconds, or config",
            )
        from domain.entities.scanner_tool_settings import ScannerToolSettings
        row = ScannerToolSettings(
            scanner_key=tk,
            enabled=body.enabled,
            timeout_seconds=body.timeout_seconds,
            config=_merge_tool_config({}, body.config) if body.config is not None else {},
            updated_at=datetime.utcnow(),
            updated_by_user_id=uid,
        )
    else:
        if body.enabled is not None:
            row.enabled = body.enabled
        if body.timeout_seconds is not None:
            row.timeout_seconds = body.timeout_seconds
        if body.config is not None:
            row.config = _merge_tool_config(row.config, body.config)
        row.updated_at = datetime.utcnow()
        row.updated_by_user_id = uid
    await settings_repo.save(row)
    await AuditLogService.log_event(
        user_id=actor_context.user_id,
        user_email=actor_context.email,
        action_type="SCANNER_TOOL_SETTINGS_UPDATED",
        target=tk,
        details={"timeout": body.timeout_seconds, "enabled": body.enabled},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    return {"ok": True, "tools_key": tk}


@router.delete("/scanner-tool-settings/{tools_key:path}")
async def delete_scanner_tool_settings(
    tools_key: str,
    request: Request,
    actor_context: ActorContext = Depends(get_admin_user),
    scanner_repo: ScannerRepositoryInterface = Depends(lambda: get_scanner_repository()),
    settings_repo: ScannerToolSettingsRepository = Depends(lambda: get_scanner_tool_settings_repository()),
) -> Dict[str, Any]:
    sc = await scanner_repo.get_by_tools_key(tools_key)
    if not sc:
        raise HTTPException(status_code=404, detail=f"Unknown tools_key: {tools_key}")
    tk = _tools_key_from_scanner_entity(sc)
    if not tk:
        raise HTTPException(status_code=404, detail=f"Scanner has no tools_key: {tools_key}")
    await settings_repo.delete_by_key(tk)
    await AuditLogService.log_event(
        user_id=actor_context.user_id,
        user_email=actor_context.email,
        action_type="SCANNER_TOOL_SETTINGS_CLEARED",
        target=tk,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    return {"ok": True, "tools_key": tk}
