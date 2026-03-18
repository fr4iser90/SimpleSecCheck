"""
Who may read scan results (report, API scan detail, steps, …).

- Owner: logged-in user_id matches scan.user_id, or guest session_id in scan_metadata.
- Share — DB JSON scan_metadata:
  - report_shared_with_user_ids: list of user UUID strings (read-only for those users).
  - report_share_token: secret (≥8 chars); pass ?share_token= on report URL.
Mutations (update/delete/cancel/retry): owner only (see is_scan_owner).
"""
from __future__ import annotations

import secrets
from typing import Any, Dict, Optional


def _norm_uuid(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return None
    try:
        from uuid import UUID

        return str(UUID(str(value))).lower()
    except (ValueError, TypeError):
        return str(value).strip().lower() or None


def is_scan_owner(
    *,
    metadata: Dict[str, Any],
    scan_user_id: Optional[str],
    actor_user_id: Optional[str],
    actor_session_id: Optional[str],
    actor_is_authenticated: bool,
) -> bool:
    meta = metadata or {}
    if actor_is_authenticated and actor_user_id:
        uid = _norm_uuid(actor_user_id)
        if uid and scan_user_id and _norm_uuid(str(scan_user_id)) == uid:
            return True
        return False
    if not actor_is_authenticated and actor_session_id:
        return str(meta.get("session_id") or "") == str(actor_session_id)
    return False


def can_read_scan_results(
    *,
    metadata: Dict[str, Any],
    scan_user_id: Optional[str],
    actor_user_id: Optional[str],
    actor_session_id: Optional[str],
    actor_is_authenticated: bool,
    share_token_query: Optional[str] = None,
) -> bool:
    meta = metadata or {}

    if share_token_query:
        expected = meta.get("report_share_token")
        if isinstance(expected, str) and len(expected) >= 8:
            try:
                if secrets.compare_digest(share_token_query, expected):
                    return True
            except TypeError:
                pass

    if is_scan_owner(
        metadata=meta,
        scan_user_id=scan_user_id,
        actor_user_id=actor_user_id,
        actor_session_id=actor_session_id,
        actor_is_authenticated=actor_is_authenticated,
    ):
        return True

    if actor_is_authenticated and actor_user_id:
        uid = _norm_uuid(actor_user_id)
        shared = meta.get("report_shared_with_user_ids") or meta.get("shared_with_user_ids")
        if shared and isinstance(shared, (list, tuple)) and uid:
            allowed = {_norm_uuid(str(x)) for x in shared if x}
            if uid in allowed:
                return True

    return False
