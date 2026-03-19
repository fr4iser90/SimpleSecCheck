"""Database ScanSteps read repository (DDD)."""
import json
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from domain.repositories.scan_steps_repository import ScanStepsRepository
from infrastructure.database.adapter import db_adapter


def _dt_to_iso_z(dt: Any) -> Optional[str]:
    if dt is None:
        return None
    from datetime import datetime, timezone
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
    if isinstance(dt, str):
        return dt
    return None


class DatabaseScanStepsRepository(ScanStepsRepository):
    """PostgreSQL implementation of ScanStepsRepository (raw SQL; no ORM model)."""

    def __init__(self, db_adapter_instance=None):
        self.db_adapter = db_adapter_instance or db_adapter

    async def get_steps_for_scan(self, scan_id: str) -> Optional[List[Dict[str, Any]]]:
        try:
            await self.db_adapter.ensure_initialized()
        except Exception:
            return None
        try:
            async with self.db_adapter.async_session() as session:
                result = await session.execute(
                    text(
                        """
                        SELECT step_number, step_name, status, message,
                               started_at, completed_at, substeps, timeout_seconds
                        FROM scan_steps
                        WHERE scan_id = :sid
                        ORDER BY step_number ASC
                        """
                    ),
                    {"sid": scan_id},
                )
                rows = result.fetchall()
        except Exception:
            return None
        if not rows:
            return None
        steps: List[Dict[str, Any]] = []
        for row in rows:
            sn, sname, st, msg, sa, ca, subs, to = (
                row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7],
            )
            substeps: List[Dict[str, Any]] = []
            if subs is not None:
                if isinstance(subs, str):
                    try:
                        substeps = json.loads(subs) if subs else []
                    except json.JSONDecodeError:
                        substeps = []
                elif isinstance(subs, list):
                    substeps = subs
            step = {
                "number": int(sn),
                "name": sname or "Unknown",
                "status": st or "pending",
                "message": msg or "",
                "started_at": _dt_to_iso_z(sa),
                "completed_at": _dt_to_iso_z(ca),
                "substeps": [
                    {
                        "name": (ss.get("name") or "") if isinstance(ss, dict) else "",
                        "status": (ss.get("status") or "pending") if isinstance(ss, dict) else "pending",
                        "message": (ss.get("message") or "") if isinstance(ss, dict) else "",
                        "started_at": ss.get("started_at") if isinstance(ss, dict) else None,
                        "completed_at": ss.get("completed_at") if isinstance(ss, dict) else None,
                        "type": (ss.get("type") or "action") if isinstance(ss, dict) else "action",
                    }
                    for ss in substeps
                ],
                "timeout_seconds": int(to) if to is not None else None,
            }
            steps.append(step)
        return steps
