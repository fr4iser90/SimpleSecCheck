"""
Redis-backed status for scanner asset (vuln DB) updates.

Keeps admin Update buttons disabled while a job is running.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

REDIS_KEY = "simpleseccheck:scanner_asset_update:status"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _default_idle() -> Dict[str, Any]:
    return {
        "status": "idle",
        "started_at": None,
        "finished_at": None,
        "error_message": None,
        "exit_code": None,
        "scanner": None,
        "asset_id": None,
    }


async def get_asset_update_status() -> Dict[str, Any]:
    from infrastructure.redis.client import redis_client

    try:
        if not redis_client.is_connected:
            await redis_client.connect()
        raw = await redis_client.get(REDIS_KEY)
        if not raw:
            return _default_idle()
        data = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(data, dict):
            return _default_idle()
        out = _default_idle()
        out.update({k: data.get(k) for k in out.keys()})
        return out
    except Exception as e:
        logger.warning("Could not read asset update status: %s", e)
        return _default_idle()


async def set_asset_update_status(payload: Dict[str, Any], *, ttl_seconds: int = 86400) -> None:
    from infrastructure.redis.client import redis_client

    try:
        if not redis_client.is_connected:
            await redis_client.connect()
        merged = _default_idle()
        merged.update(payload)
        await redis_client.set(REDIS_KEY, json.dumps(merged), expire=ttl_seconds)
    except Exception as e:
        logger.warning("Could not write asset update status: %s", e)


async def mark_asset_update_running(*, scanner: str, asset_id: str) -> Dict[str, Any]:
    payload = {
        "status": "running",
        "started_at": _utcnow_iso(),
        "finished_at": None,
        "error_message": None,
        "exit_code": None,
        "scanner": scanner,
        "asset_id": asset_id,
    }
    await set_asset_update_status(payload)
    return payload


async def mark_asset_update_finished(
    *,
    ok: bool,
    exit_code: Optional[int] = None,
    error_message: Optional[str] = None,
    scanner: Optional[str] = None,
    asset_id: Optional[str] = None,
) -> Dict[str, Any]:
    current = await get_asset_update_status()
    payload = {
        "status": "done" if ok else "error",
        "started_at": current.get("started_at"),
        "finished_at": _utcnow_iso(),
        "error_message": error_message,
        "exit_code": exit_code,
        "scanner": scanner or current.get("scanner"),
        "asset_id": asset_id or current.get("asset_id"),
    }
    await set_asset_update_status(payload)
    return payload
