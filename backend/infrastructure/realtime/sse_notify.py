"""Fire-and-forget helpers for SSE fan-out from route handlers (structured envelopes)."""
from __future__ import annotations

from typing import Any, Dict, Optional

from infrastructure.realtime.sse_manager import sse_broadcast_envelope, sse_emit_envelope

SSE_ENVELOPE_VERSION = 1
GUEST_SSE_PREFIX = "guest:"


def make_envelope(typ: str, scope: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "v": SSE_ENVELOPE_VERSION,
        "type": typ,
        "scope": scope,
        "payload": payload,
    }


def sse_subscriber_key(
    user_id: Optional[str], guest_session_id: Optional[str] = None
) -> Optional[str]:
    if user_id:
        return str(user_id)
    if guest_session_id:
        return f"{GUEST_SSE_PREFIX}{guest_session_id}"
    return None


async def sse_emit_to_actor(
    user_id: Optional[str],
    guest_session_id: Optional[str],
    envelope: Dict[str, Any],
) -> None:
    key = sse_subscriber_key(user_id, guest_session_id)
    if not key:
        return
    await sse_emit_envelope(key, envelope)


async def sse_notify_scan(
    user_id: Optional[str],
    scan_id: str,
    status: Optional[str] = None,
    *,
    guest_session_id: Optional[str] = None,
    list_revision: Optional[str] = None,
    position: Optional[int] = None,
) -> None:
    """Notify scan activity for the owning user or guest session."""
    if not user_id and not guest_session_id:
        return
    rev = list_revision
    if rev is None and user_id:
        from api.helpers.user_targets_revision import compute_user_targets_list_revision

        rev = await compute_user_targets_list_revision(str(user_id))
    elif rev is None:
        rev = ""
    payload: Dict[str, Any] = {
        "scan_id": scan_id,
        "status": status or "updated",
        "list_revision": rev,
    }
    if position is not None:
        payload["position"] = position
    await sse_emit_to_actor(
        user_id,
        guest_session_id,
        make_envelope("scan_update", "all", payload),
    )


async def sse_notify_queue_changed(
    *, reason: str = "updated", scan_id: Optional[str] = None
) -> None:
    """Broadcast queue invalidation to all SSE subscribers (public queue page)."""
    payload: Dict[str, Any] = {"reason": reason}
    if scan_id:
        payload["scan_id"] = scan_id
    await sse_broadcast_envelope(make_envelope("queue_update", "queue", payload))


async def sse_notify_target_upsert(
    user_id: Optional[str], target: Dict[str, Any], list_revision: str
) -> None:
    if not user_id:
        return
    await sse_emit_envelope(
        str(user_id),
        make_envelope(
            "target_update",
            "targets",
            {"action": "upsert", "target": target, "list_revision": list_revision},
        ),
    )


async def sse_notify_target_remove(
    user_id: Optional[str], target_id: str, list_revision: str
) -> None:
    if not user_id:
        return
    await sse_emit_envelope(
        str(user_id),
        make_envelope(
            "target_update",
            "targets",
            {"action": "remove", "target_id": target_id, "list_revision": list_revision},
        ),
    )


async def sse_notify_target_refetch(
    user_id: Optional[str], list_revision: str
) -> None:
    """Client should GET `/targets` with If-None-Match (light invalidation)."""
    if not user_id:
        return
    await sse_emit_envelope(
        str(user_id),
        make_envelope(
            "target_update",
            "targets",
            {"action": "refetch", "list_revision": list_revision},
        ),
    )
