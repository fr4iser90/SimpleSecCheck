"""
Server-Sent Events (SSE) — global push for signed-in users and guest sessions.

Auth: EventSource uses same-origin cookies (refresh_token for users, session_id for guests).
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from api.deps.actor_context import ActorContext, get_actor_context
from infrastructure.realtime.sse_manager import sse_subscribe, sse_unsubscribe
from infrastructure.realtime.sse_notify import GUEST_SSE_PREFIX, make_envelope

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["events"])

SSC_EVENT = "ssc"


def _format_ssc(envelope: dict) -> str:
    return f"event: {SSC_EVENT}\ndata: {json.dumps(envelope, separators=(',', ':'))}\n\n"


def _resolve_sse_subscriber_key(actor: ActorContext) -> str:
    if actor.is_authenticated and actor.user_id:
        return str(actor.user_id)
    if actor.session_id:
        return f"{GUEST_SSE_PREFIX}{actor.session_id}"
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session required",
    )


@router.get("/events/stream")
async def events_stream(
    actor: ActorContext = Depends(get_actor_context),
) -> StreamingResponse:
    """Long-lived SSE stream; payloads use `event: ssc` with JSON envelope (v, type, scope, payload)."""
    sub_key = _resolve_sse_subscriber_key(actor)

    async def gen() -> AsyncIterator[str]:
        q = await sse_subscribe(sub_key)
        connected_payload: dict = {"kind": "connected"}
        if actor.is_authenticated and actor.user_id:
            connected_payload["user_id"] = str(actor.user_id)
        elif actor.session_id:
            connected_payload["guest_session_id"] = actor.session_id
        try:
            yield _format_ssc(
                make_envelope(
                    "system",
                    "none",
                    connected_payload,
                )
            )
            while True:
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=25.0)
                    if isinstance(msg, dict) and msg.get("v") == 1:
                        yield _format_ssc(msg)
                    else:
                        logger.debug("SSE: skip non-envelope message for %s", sub_key)
                except asyncio.TimeoutError:
                    yield _format_ssc(
                        make_envelope("system", "none", {"kind": "ping"})
                    )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("SSE stream error for %s", sub_key)
        finally:
            await sse_unsubscribe(sub_key, q)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
