"""
Read system_state without backend ORM models.

The worker Docker image only ships ``worker/``; ``infrastructure.database.models``
is not available. A failed import was previously swallowed, so ``max_concurrent_jobs``
from the DB was never applied (worker always fell back to 1 slot).
"""

from __future__ import annotations

from typing import Any, Tuple

from sqlalchemy import text


async def read_worker_system_state(database_adapter: Any) -> Tuple[bool, int | None]:
    """
    Returns (setup_complete, db_max_concurrent_jobs).

    ``db_max_concurrent_jobs`` is None if unset or unreadable.
    """
    setup_complete = False
    db_max_jobs: int | None = None
    try:
        async with database_adapter.get_session() as session:
            r = await session.execute(
                text("SELECT to_regclass(:table_name)"),
                {"table_name": "public.system_state"},
            )
            if r.scalar() is None:
                return setup_complete, db_max_jobs

            r2 = await session.execute(
                text(
                    """
                    SELECT setup_status, setup_locked, database_initialized,
                           admin_user_created, system_configured, config
                    FROM system_state
                    LIMIT 1
                    """
                )
            )
            row = r2.fetchone()
            if not row:
                return setup_complete, db_max_jobs

            ss, sl, di, auc, scf, cfg = row
            raw = ss if isinstance(ss, str) else getattr(ss, "value", str(ss)) or ""
            st = str(raw).split(".")[-1].lower()
            setup_complete = bool(
                st in ("completed", "locked")
                and sl
                and di
                and auc
                and scf
            )

            if isinstance(cfg, dict):
                raw = cfg.get("max_concurrent_jobs")
                if raw is None:
                    raw = cfg.get("max_concurrent_scans")
                if raw is not None:
                    try:
                        db_max_jobs = max(1, min(50, int(raw)))
                    except (TypeError, ValueError):
                        db_max_jobs = None
    except Exception:
        pass

    return setup_complete, db_max_jobs
