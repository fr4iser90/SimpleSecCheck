"""Fire-and-forget helpers for SSE fan-out from route handlers (structured envelopes)."""
from __future__ import annotations

from typing import Any, Dict, Optional

from infrastructure.realtime.sse_manager import sse_emit_envelope

SSE_ENVELOPE_VERSION = 1


def make_envelope(typ: str, scope: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "v": SSE_ENVELOPE_VERSION,
        "type": typ,
        "scope": scope,
        "payload": payload,
    }


async def sse_notify_scan(
    user_id: Optional[str],
    scan_id: str,
    status: Optional[str] = None,
    *,
    list_revision: Optional[str] = None,
) -> None:
    """Notify scan activity; always includes `list_revision` so clients can skip target GET when unchanged."""
    if not user_id:
        return
    rev = list_revision
    if rev is None:
        from api.helpers.user_targets_revision import compute_user_targets_list_revision

        rev = await compute_user_targets_list_revision(str(user_id))
    await sse_emit_envelope(
        str(user_id),
        make_envelope(
            "scan_update",
            "all",
            {
                "scan_id": scan_id,
                "status": status or "updated",
                "list_revision": rev,
            },
        ),
    )


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
