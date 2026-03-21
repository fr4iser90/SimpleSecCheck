"""
Subscribe to Redis pub/sub channel `scan_events` and forward to per-user SSE queues.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional

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


async def run_redis_sse_bridge(stop: asyncio.Event) -> None:
    """Loop until stop is set. Safe to cancel via stop.set()."""
    try:
        from api.helpers.user_targets_revision import compute_user_targets_list_revision
        from infrastructure.redis.client import redis_client
        from infrastructure.realtime.sse_notify import make_envelope, sse_emit_envelope
    except Exception as e:
        logger.warning("SSE Redis bridge not started: %s", e)
        return

    pubsub = None
    try:
        pubsub = await redis_client.subscribe(SCAN_EVENTS_CHANNEL)
        if pubsub is None:
            logger.warning("SSE Redis bridge: subscribe returned None")
            return
        logger.info("SSE Redis bridge listening on %s", SCAN_EVENTS_CHANNEL)
        while not stop.is_set():
            try:
                msg = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True),
                    timeout=1.0,
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("SSE Redis bridge get_message error")
                await asyncio.sleep(2)
                continue
            if not msg or msg.get("type") != "message":
                continue
            raw = msg.get("data")
            if raw is None:
                continue
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="replace")
            try:
                data = json.loads(raw) if isinstance(raw, str) else raw
            except (json.JSONDecodeError, TypeError):
                logger.debug("SSE bridge: skip non-JSON message")
                continue
            if not isinstance(data, dict):
                continue
            user_id = await _user_id_for_scan_event(data)
            if not user_id:
                logger.warning(
                    "SSE Redis bridge: drop scan_events message (no user_id): scan_id=%s type=%s",
                    data.get("scan_id"),
                    data.get("type"),
                )
                continue
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
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception("SSE Redis bridge crashed")
    finally:
        if pubsub is not None:
            try:
                await pubsub.unsubscribe(SCAN_EVENTS_CHANNEL)
                await pubsub.close()
            except Exception:
                logger.debug("pubsub close failed", exc_info=True)
