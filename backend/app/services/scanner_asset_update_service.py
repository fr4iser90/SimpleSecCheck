"""
Scanner Asset Update Service
Generic update lifecycle management for scanner assets
"""
from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

from app.services.scanner_assets_service import update_scanner_asset


@dataclass
class AssetUpdateStatus:
    status: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error_message: Optional[str] = None
    exit_code: Optional[int] = None


current_update: Dict[str, Any] = {
    "status": "idle",
    "started_at": None,
    "finished_at": None,
    "error_message": None,
    "exit_code": None,
    "lock": threading.Lock(),
}


async def start_asset_update(scanner_name: str, asset_id: str) -> AssetUpdateStatus:
    with current_update["lock"]:
        if current_update["status"] == "running":
            return AssetUpdateStatus(status="running", started_at=current_update["started_at"])
        current_update["status"] = "running"
        current_update["started_at"] = datetime.now().isoformat()
        current_update["finished_at"] = None
        current_update["error_message"] = None
        current_update["exit_code"] = None

    async def _run():
        try:
            result = update_scanner_asset(scanner_name, asset_id)
            current_update["exit_code"] = result.get("exit_code")
            if result.get("exit_code") == 0:
                current_update["status"] = "done"
            else:
                current_update["status"] = "error"
                current_update["error_message"] = f"Update failed with exit code {result.get('exit_code')}"
        except Exception as exc:
            current_update["status"] = "error"
            current_update["error_message"] = str(exc)
        finally:
            current_update["finished_at"] = datetime.now().isoformat()

    asyncio.create_task(_run())
    return AssetUpdateStatus(status="running", started_at=current_update["started_at"])


def get_asset_update_status() -> AssetUpdateStatus:
    return AssetUpdateStatus(
        status=current_update["status"],
        started_at=current_update["started_at"],
        finished_at=current_update["finished_at"],
        error_message=current_update["error_message"],
        exit_code=current_update["exit_code"],
    )
