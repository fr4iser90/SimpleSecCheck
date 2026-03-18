"""
Enforce admin-configured scan policies and rate limits before creating a scan.
Config lives in SystemState.config: execution_limits, policies.
"""
from __future__ import annotations

import fnmatch
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select

from application.dtos.request_dto import ScanRequestDTO
from domain.entities.target_type import TargetType
from domain.exceptions.scan_exceptions import (
    ScanExecutionRateLimitException,
    ScanPolicyBlockedException,
)
from domain.repositories.scan_repository import ScanRepository
from infrastructure.database.adapter import db_adapter
from infrastructure.database.models import SystemState

logger = logging.getLogger(__name__)


def _target_matches_blocked_pattern(target_url: str, pattern: str) -> bool:
    p = (pattern or "").strip()
    if not p:
        return False
    if p.lower().startswith("regex:"):
        try:
            return bool(re.search(p[6:].strip(), target_url, re.IGNORECASE))
        except re.error:
            logger.warning("Invalid regex in blocked_target_patterns: %s", p[:80])
            return False
    return fnmatch.fnmatch(target_url, p) or fnmatch.fnmatch(target_url.lower(), p.lower())


def _check_policies(request: ScanRequestDTO, policies: Dict[str, Any]) -> None:
    policies = policies or {}
    target = (request.target_url or "").strip()
    for pat in policies.get("blocked_target_patterns") or []:
        if isinstance(pat, str) and _target_matches_blocked_pattern(target, pat):
            raise ScanPolicyBlockedException(
                f"Target is blocked by policy (pattern matched: {pat!r})."
            )
    st = request.scan_type.value.lower() if hasattr(request.scan_type, "value") else str(request.scan_type).lower()
    for blocked in policies.get("blocked_scan_types") or []:
        b = (blocked or "").strip().lower()
        if b and st == b:
            raise ScanPolicyBlockedException(
                f"Scan type '{st}' is blocked by system policy."
            )
    if policies.get("require_auth_for_git"):
        tt = (request.target_type or "").lower()
        if tt == TargetType.GIT_REPO.value and not request.user_id:
            raise ScanPolicyBlockedException(
                "Git repository scans require authentication (policy: require_auth_for_git)."
            )


async def _load_limits_and_policies() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    try:
        await db_adapter.ensure_initialized()
        async with db_adapter.async_session() as session:
            r = await session.execute(select(SystemState).limit(1))
            ss = r.scalar_one_or_none()
            cfg = (ss.config or {}) if ss else {}
            return (cfg.get("execution_limits") or {}, cfg.get("policies") or {})
    except Exception as e:
        logger.warning("scan enforcement: could not load SystemState: %s", e)
        return {}, {}


def _positive_int(v: Any) -> Optional[int]:
    if v is None:
        return None
    try:
        n = int(v)
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


async def enforce_scan_creation(
    scan_repository: ScanRepository,
    request: ScanRequestDTO,
    *,
    actor_role: str,
    guest_session_id: Optional[str],
    enforcement_mode: str = "full",
) -> None:
    """
    enforcement_mode:
      - full: policies + rate limits
      - policies_only: policies only (e.g. scan retry)
    """
    limits, policies = await _load_limits_and_policies()
    _check_policies(request, policies)
    if enforcement_mode != "full":
        return
    if actor_role == "admin" and not limits.get("rate_limit_admins"):
        return

    since = datetime.utcnow() - timedelta(hours=1)
    now = datetime.utcnow()
    next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    retry_after = max(60, int((next_hour - now).total_seconds()))

    mg = _positive_int(limits.get("max_scans_per_hour_global"))
    if mg is not None:
        n = await scan_repository.count_scans_created_since(since, global_all=True)
        if n >= mg:
            raise ScanExecutionRateLimitException(
                f"Global scan rate limit reached ({mg} scans/hour). Try again later.",
                retry_after_seconds=retry_after,
            )

    if request.user_id:
        mu = _positive_int(limits.get("max_scans_per_hour_per_user"))
        if mu is not None:
            n = await scan_repository.count_scans_created_since(
                since, user_id=str(request.user_id)
            )
            if n >= mu:
                raise ScanExecutionRateLimitException(
                    f"Your hourly scan limit is {mu}. Try again later.",
                    retry_after_seconds=retry_after,
                )
        mc = _positive_int(limits.get("max_concurrent_scans_per_user"))
        if mc is not None:
            n = await scan_repository.count_active_scans_for_actor(user_id=str(request.user_id))
            if n >= mc:
                raise ScanExecutionRateLimitException(
                    f"Maximum concurrent scans per user is {mc}. Wait for a scan to finish.",
                    retry_after_seconds=60,
                )
    elif guest_session_id:
        mguest = _positive_int(limits.get("max_scans_per_hour_per_guest_session"))
        if mguest is not None:
            n = await scan_repository.count_scans_created_since(
                since, guest_session_id=guest_session_id
            )
            if n >= mguest:
                raise ScanExecutionRateLimitException(
                    f"Guest session hourly scan limit is {mguest}. Sign in for higher limits.",
                    retry_after_seconds=retry_after,
                )
        cguest = _positive_int(limits.get("max_concurrent_scans_per_guest"))
        if cguest is not None:
            n = await scan_repository.count_active_scans_for_actor(
                guest_session_id=guest_session_id
            )
            if n >= cguest:
                raise ScanExecutionRateLimitException(
                    f"Maximum concurrent guest scans is {cguest}.",
                    retry_after_seconds=60,
                )


async def get_max_scan_wall_seconds() -> int:
    """Worker container wait timeout (seconds), from execution_limits.max_scan_duration_seconds."""
    default = 3600
    try:
        await db_adapter.ensure_initialized()
        async with db_adapter.async_session() as session:
            r = await session.execute(select(SystemState).limit(1))
            ss = r.scalar_one_or_none()
            if not ss:
                return default
            el = (ss.config or {}).get("execution_limits") or {}
            v = _positive_int(el.get("max_scan_duration_seconds"))
            if v is None:
                return default
            return max(300, min(86400, v))
    except Exception:
        return default
