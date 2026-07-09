"""
Redis scan_events → bounded asyncio.Queue → delivery to per-user SSE (Level 3).

- IO (Redis PubSub) is decoupled from fan-out (sse_emit_envelope).
- Backpressure: when the queue is full, the Redis listener awaits put() until space is free.
- Uses pubsub.listen() (event-driven, blocks until data) instead of get_message() polling.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional, Tuple

from config.settings import get_settings

logger = logging.getLogger(__name__)

SCAN_EVENTS_CHANNEL = "scan_events"

# Short TTL: many scan_events per second would otherwise each run a full targets-list query.
_list_rev_memo: Dict[str, Tuple[float, str]] = {}
_LIST_REV_MEMO_TTL_SEC = 2.5
_LIST_REV_MEMO_MAX_KEYS = 2000


async def _list_revision_for_sse(user_id: str) -> str:
    """Compute targets list_revision with per-user memoization (reduces DB load on event bursts)."""
    from api.helpers.user_targets_revision import compute_user_targets_list_revision

    now = time.monotonic()
    row = _list_rev_memo.get(user_id)
    if row is not None and (now - row[0]) < _LIST_REV_MEMO_TTL_SEC:
        return row[1]
    rev = await compute_user_targets_list_revision(user_id)
    _list_rev_memo[user_id] = (now, rev)
    if len(_list_rev_memo) > _LIST_REV_MEMO_MAX_KEYS:
        cutoff = now - _LIST_REV_MEMO_TTL_SEC * 4
        stale = [k for k, (t, _) in _list_rev_memo.items() if t < cutoff]
        for k in stale[: _LIST_REV_MEMO_MAX_KEYS // 2]:
            _list_rev_memo.pop(k, None)
    return rev


async def _guest_session_id_for_scan(scan_id: str) -> Optional[str]:
    try:
        from infrastructure.container import get_scan_repository

        repo = get_scan_repository()
        scan = await repo.get_by_id(str(scan_id))
        if not scan:
            return None
        meta = getattr(scan, "scan_metadata", None) or {}
        if isinstance(meta, dict):
            gsid = meta.get("session_id")
            return str(gsid) if gsid else None
    except Exception:
        logger.debug("SSE bridge: guest session lookup failed", exc_info=True)
    return None


async def _recipient_keys_for_scan_event(data: Dict[str, Any]) -> list[str]:
    """Resolve SSE subscriber keys (user_id and/or guest:session_id) for a scan_events payload."""
    from infrastructure.realtime.sse_notify import GUEST_SSE_PREFIX, sse_subscriber_key

    user_id = data.get("user_id")
    guest_session_id = data.get("guest_session_id")
    if user_id or guest_session_id:
        key = sse_subscriber_key(
            str(user_id) if user_id else None,
            str(guest_session_id) if guest_session_id else None,
        )
        return [key] if key else []

    scan_id = data.get("scan_id")
    if not scan_id:
        return []

    keys: list[str] = []
    try:
        from infrastructure.container import get_scan_repository

        repo = get_scan_repository()
        scan = await repo.get_by_id(str(scan_id))
        if scan and getattr(scan, "user_id", None):
            keys.append(str(scan.user_id))
        gsid = await _guest_session_id_for_scan(str(scan_id))
        guest_key = sse_subscriber_key(None, gsid)
        if guest_key and guest_key not in keys:
            keys.append(guest_key)
    except Exception:
        logger.debug("SSE bridge: scan owner lookup failed", exc_info=True)
    return keys


async def _deliver_scan_event_payload(data: Dict[str, Any]) -> None:
    """Resolve owners, emit scan_update to each, broadcast queue_update."""
    from infrastructure.realtime.sse_notify import (
        make_envelope,
        sse_emit_envelope,
        sse_notify_queue_changed,
    )

    recipient_keys = await _recipient_keys_for_scan_event(data)
    if not recipient_keys:
        logger.warning(
            "SSE Redis bridge: drop scan_events message (no recipient): scan_id=%s type=%s",
            data.get("scan_id"),
            data.get("type"),
        )
        return

    list_rev = ""
    primary_user = data.get("user_id")
    if not primary_user and recipient_keys and not recipient_keys[0].startswith("guest:"):
        primary_user = recipient_keys[0]
    if primary_user and not str(primary_user).startswith("guest:"):
        try:
            list_rev = await _list_revision_for_sse(str(primary_user))
        except Exception:
            logger.exception("SSE Redis bridge: list revision failed for user %s", primary_user)
            list_rev = ""

    envelope = make_envelope(
        "scan_update",
        "all",
        {
            "source": "redis",
            "event_type": data.get("type", "scan_event"),
            "scan_id": data.get("scan_id"),
            "status": data.get("status"),
            "list_revision": list_rev,
        },
    )
    for key in recipient_keys:
        await sse_emit_envelope(key, envelope)

    await sse_notify_queue_changed(
        reason=str(data.get("type") or data.get("status") or "updated"),
        scan_id=str(data.get("scan_id")) if data.get("scan_id") else None,
    )


async def _redis_io_loop(
    pubsub: Any,
    queue: "asyncio.Queue[Dict[str, Any]]",
    stop: asyncio.Event,
) -> None:
    """
    Single reader: async for msg in pubsub.listen() — blocks until Redis delivers (no busy spin).
    Parsed dicts are put on the queue (blocking put = backpressure).
    """
    try:
        async for raw in pubsub.listen():
            if stop.is_set():
                break
            if not raw or raw.get("type") != "message":
                continue
            payload = raw.get("data")
            if payload is None:
                continue
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8", errors="replace")
            try:
                data = json.loads(payload) if isinstance(payload, str) else payload
            except (json.JSONDecodeError, TypeError):
                logger.debug("SSE bridge: skip non-JSON message")
                continue
            if not isinstance(data, dict):
                continue
            await queue.put(data)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("SSE Redis bridge: listen loop error")
        raise
    finally:
        stop.set()
        try:
            await pubsub.unsubscribe(SCAN_EVENTS_CHANNEL)
        except Exception:
            logger.debug("pubsub unsubscribe failed", exc_info=True)
        try:
            await pubsub.close()
        except Exception:
            logger.debug("pubsub close failed", exc_info=True)


async def _delivery_loop(
    queue: "asyncio.Queue[Dict[str, Any]]",
    stop: asyncio.Event,
) -> None:
    """Consume parsed events from the queue and fan out to SSE.
    
    Optimierte Version ohne asyncio.wait() Overhead:
    Nutzt asyncio.as_completed() statt wait() für minimalen Event Loop Last
    """
    while not stop.is_set():
        try:
            # Warte gleichzeitig auf Stop Event oder neue Nachricht
            get_task = asyncio.create_task(queue.get())
            stop_task = asyncio.create_task(stop.wait())
            
            for coro in asyncio.as_completed([get_task, stop_task]):
                result = await coro
                if coro is stop_task:
                    get_task.cancel()
                    try:
                        await get_task
                    except asyncio.CancelledError:
                        pass
                    return
                if coro is get_task:
                    stop_task.cancel()
                    try:
                        await stop_task
                    except asyncio.CancelledError:
                        pass
                    data = result
                    break
            
            await _deliver_scan_event_payload(data)
            
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("SSE Redis bridge: delivery failed")
            await asyncio.sleep(0.5)


async def run_redis_sse_bridge(stop: asyncio.Event) -> None:
    """Run Redis listener + delivery worker until cancelled or the listen loop ends."""
    try:
        from infrastructure.redis.client import redis_client
    except Exception as e:
        logger.warning("SSE Redis bridge not started: %s", e)
        return

    pair = await redis_client.subscribe(SCAN_EVENTS_CHANNEL)
    if pair is None:
        logger.warning("SSE Redis bridge: subscribe returned None")
        return
    pubsub, pub_redis = pair

    maxsize = get_settings().SSE_REDIS_BRIDGE_QUEUE_MAX
    queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=maxsize)
    logger.info(
        "SSE Redis bridge: queue maxsize=%s channel=%s (listen + delivery)",
        maxsize,
        SCAN_EVENTS_CHANNEL,
    )

    io_task = asyncio.create_task(_redis_io_loop(pubsub, queue, stop), name="redis_scan_events_io")
    delivery_task = asyncio.create_task(_delivery_loop(queue, stop), name="redis_scan_events_delivery")

    try:
        await asyncio.gather(io_task, delivery_task)
    except asyncio.CancelledError:
        stop.set()
        io_task.cancel()
        delivery_task.cancel()
        await asyncio.gather(io_task, delivery_task, return_exceptions=True)
        raise
    finally:
        try:
            await pub_redis.close()
        except Exception:
            logger.debug("SSE Redis bridge: dedicated pubsub Redis close failed", exc_info=True)
