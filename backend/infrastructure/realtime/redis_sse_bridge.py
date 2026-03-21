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
from typing import Any, Dict, Optional

from config.settings import get_settings

logger = logging.getLogger(__name__)

SCAN_EVENTS_CHANNEL = "scan_events"


async def _user_id_for_scan_event(data: Dict[str, Any]) -> Optional[str]:
    uid = data.get("user_id")
    if uid:
        return str(uid)
    scan_id = data.get("scan_id")
    if not scan_id:
        return None
    try:
        from infrastructure.container import get_scan_repository

        repo = get_scan_repository()
        scan = await repo.get_by_id(str(scan_id))
        if scan and getattr(scan, "user_id", None):
            return str(scan.user_id)
    except Exception:
        logger.debug("SSE bridge: lookup user_id for scan failed", exc_info=True)
    return None


async def _deliver_scan_event_payload(data: Dict[str, Any]) -> None:
    """Resolve user, compute revision, emit to SSE — same behaviour as before."""
    from api.helpers.user_targets_revision import compute_user_targets_list_revision
    from infrastructure.realtime.sse_notify import make_envelope, sse_emit_envelope

    user_id = await _user_id_for_scan_event(data)
    if not user_id:
        logger.warning(
            "SSE Redis bridge: drop scan_events message (no user_id): scan_id=%s type=%s",
            data.get("scan_id"),
            data.get("type"),
        )
        return
    try:
        list_rev = await compute_user_targets_list_revision(user_id)
    except Exception:
        logger.exception("SSE Redis bridge: list revision failed for user %s", user_id)
        list_rev = ""
    await sse_emit_envelope(
        user_id,
        make_envelope(
            "scan_update",
            "all",
            {
                "source": "redis",
                "event_type": data.get("type", "scan_event"),
                "scan_id": data.get("scan_id"),
                "status": data.get("status"),
                "list_revision": list_rev,
            },
        ),
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
    """Consume parsed events from the queue and fan out to SSE."""
    while not stop.is_set():
        try:
            data = await asyncio.wait_for(queue.get(), timeout=0.5)
        except asyncio.TimeoutError:
            continue
        except asyncio.CancelledError:
            break
        try:
            await _deliver_scan_event_payload(data)
        except Exception:
            logger.exception("SSE Redis bridge: delivery failed")


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
