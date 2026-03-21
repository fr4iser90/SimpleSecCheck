"""
Server-Sent Events (SSE) for authenticated users — global push (targets, scan queue hints).

Auth: native EventSource cannot send Bearer headers — same-origin + refresh_token cookie (see docs/CONFIGURATION.md §6). FastAPI dependency still accepts Bearer on other routes.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from api.deps.actor_context import ActorContext, get_authenticated_user
from infrastructure.realtime.sse_manager import sse_subscribe, sse_unsubscribe
from infrastructure.realtime.sse_notify import make_envelope

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["events"])

SSC_EVENT = "ssc"


def _format_ssc(envelope: dict) -> str:
    return f"event: {SSC_EVENT}\ndata: {json.dumps(envelope, separators=(',', ':'))}\n\n"


@router.get("/events/stream")
async def events_stream(
    actor: ActorContext = Depends(get_authenticated_user),
) -> StreamingResponse:
    """Long-lived SSE stream; all payloads use `event: ssc` with JSON envelope (v, type, scope, payload)."""
    user_id = actor.user_id
    if not user_id:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    uid = str(user_id)

    async def gen() -> AsyncIterator[str]:
        q = await sse_subscribe(uid)
        try:
            yield _format_ssc(
                make_envelope(
                    "system",
                    "none",
                    {"kind": "connected", "user_id": uid},
                )
            )
            while True:
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=25.0)
                    if isinstance(msg, dict) and msg.get("v") == 1:
                        yield _format_ssc(msg)
                    else:
                        logger.debug("SSE: skip non-envelope message for user %s", uid)
                except asyncio.TimeoutError:
                    yield _format_ssc(
                        make_envelope("system", "none", {"kind": "ping"})
                    )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("SSE stream error for user %s", uid)
        finally:
            await sse_unsubscribe(uid, q)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
