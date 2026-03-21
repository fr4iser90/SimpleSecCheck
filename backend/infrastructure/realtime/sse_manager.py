"""
In-process SSE fan-out: one asyncio.Queue per open EventSource, keyed by user_id.

Each HTTP client must call sse_unsubscribe in a finally block when the stream ends
(client disconnect, task cancel) so queues are not leaked.
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, DefaultDict, Dict, List

logger = logging.getLogger(__name__)

_lock = asyncio.Lock()
_subscribers: DefaultDict[str, List[asyncio.Queue]] = defaultdict(list)

MAX_QUEUE = 200


async def sse_subscribe(user_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=MAX_QUEUE)
    async with _lock:
        _subscribers[user_id].append(q)
    return q


async def sse_unsubscribe(user_id: str, q: asyncio.Queue) -> None:
    async with _lock:
        lst = _subscribers.get(user_id)
        if not lst:
            return
        if q in lst:
            lst.remove(q)
        if not lst:
            del _subscribers[user_id]


async def sse_emit_envelope(user_id: str, envelope: Dict[str, Any]) -> None:
    """Push one structured SSE envelope (`v`, `type`, `scope`, `payload`) to all connections for this user."""
    async with _lock:
        queues = list(_subscribers.get(user_id, []))
    if not queues:
        return
    for q in queues:
        try:
            q.put_nowait(envelope)
        except asyncio.QueueFull:
            logger.warning(
                "SSE queue full for user %s, dropping event %s",
                user_id,
                envelope.get("type"),
            )
