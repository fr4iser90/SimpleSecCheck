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

from config.settings import get_settings

logger = logging.getLogger(__name__)

_lock = asyncio.Lock()
_subscribers: DefaultDict[str, List[asyncio.Queue]] = defaultdict(list)


async def sse_subscribe(user_id: str) -> asyncio.Queue:
    maxsize = get_settings().SSE_QUEUE_MAX_PER_CONNECTION
    q: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
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


def _put_envelope_on_queues(queues: List[asyncio.Queue], envelope: Dict[str, Any], label: str) -> None:
    for q in queues:
        try:
            q.put_nowait(envelope)
        except asyncio.QueueFull:
            logger.warning(
                "SSE queue full for %s, dropping event %s",
                label,
                envelope.get("type"),
            )


async def sse_emit_envelope(subscriber_key: str, envelope: Dict[str, Any]) -> None:
    """Push one envelope to all connections for this subscriber key (user_id or guest:session_id)."""
    async with _lock:
        queues = list(_subscribers.get(subscriber_key, []))
    if not queues:
        return
    _put_envelope_on_queues(queues, envelope, subscriber_key)


async def sse_broadcast_envelope(envelope: Dict[str, Any]) -> None:
    """Push one envelope to every open SSE connection (e.g. public queue view)."""
    async with _lock:
        queues: List[asyncio.Queue] = []
        for lst in _subscribers.values():
            queues.extend(lst)
    if not queues:
        return
    _put_envelope_on_queues(queues, envelope, "broadcast")
