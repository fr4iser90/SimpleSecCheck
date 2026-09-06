"""
Promote duplicate sibling scans when a winner completes for the same repo+commit.

Used by the worker after a successful scan completion.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


def _commits_match(a: Optional[str], b: Optional[str], *, min_prefix_len: int = 7) -> bool:
    left = (a or "").strip().lower()
    right = (b or "").strip().lower()
    if not left or not right:
        return False
    if left == right:
        return True
    shorter, longer = (left, right) if len(left) <= len(right) else (right, left)
    return len(shorter) >= min_prefix_len and longer.startswith(shorter)


def _commit_from_meta(meta: Any) -> Optional[str]:
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except json.JSONDecodeError:
            return None
    if not isinstance(meta, dict):
        return None
    raw = meta.get("commit_hash") or meta.get("commit_sha") or meta.get("commit")
    if raw:
        return str(raw).strip() or None
    git_info = meta.get("git_info")
    if isinstance(git_info, dict):
        gh = git_info.get("commit_hash") or git_info.get("commit_sha") or git_info.get("commit")
        if gh:
            return str(gh).strip() or None
    return None


def _branch_from_config(config: Any) -> str:
    if isinstance(config, str):
        try:
            config = json.loads(config)
        except json.JSONDecodeError:
            return ""
    if not isinstance(config, dict):
        return ""
    b = config.get("git_branch") or config.get("branch") or ""
    return str(b).strip().lower()


def _symlink_results(winner_id: str, sibling_id: str) -> None:
    """Point sibling results dir at winner so /api/results/{sibling}/report works."""
    base = Path(os.environ.get("RESULTS_DIR", "/app/results"))
    winner_dir = base / winner_id
    sibling_dir = base / sibling_id
    if not winner_dir.is_dir():
        return
    try:
        if sibling_dir.is_symlink():
            sibling_dir.unlink()
        elif sibling_dir.exists():
            # Don't wipe non-empty real dirs; metadata redirect still works for findings.
            return
        sibling_dir.symlink_to(winner_dir, target_is_directory=True)
    except OSError as e:
        logger.warning("Could not symlink results %s → %s: %s", sibling_id, winner_id, e)


async def fanout_completed_scan_to_siblings(
    database_adapter: Any,
    *,
    winner_scan_id: str,
    vuln_counts: Dict[str, int],
    duration_seconds: Optional[int],
    results_json: Optional[str],
    publish_events,
) -> int:
    """
    Mark duplicate scans completed with results_from_scan_id=winner.

    Matches: same user_id + target_url, and (commit match OR awaits_results_from_scan_id).
    Returns number of siblings updated.
    """
    from sqlalchemy import text

    async with database_adapter.get_session() as session:
        row = await session.execute(
            text(
                """
                SELECT user_id, target_url, scan_metadata, config, status
                FROM scans WHERE id = :id
                """
            ),
            {"id": winner_scan_id},
        )
        winner = row.mappings().first()
        if not winner or not winner.get("user_id"):
            return 0

        user_id = winner["user_id"]
        target_url = winner.get("target_url") or ""
        winner_commit = _commit_from_meta(winner.get("scan_metadata"))
        winner_branch = _branch_from_config(winner.get("config"))

        siblings = await session.execute(
            text(
                """
                SELECT id, status, scan_metadata, config, target_url
                FROM scans
                WHERE user_id = :user_id
                  AND id <> :winner_id
                  AND status IN ('pending', 'running', 'cancelled')
                  AND target_url = :target_url
                LIMIT 100
                """
            ),
            {
                "user_id": user_id if isinstance(user_id, UUID) else UUID(str(user_id)),
                "winner_id": winner_scan_id
                if isinstance(winner_scan_id, UUID)
                else UUID(str(winner_scan_id)),
                "target_url": target_url,
            },
        )
        rows = list(siblings.mappings().all())

    promoted = 0
    now = datetime.utcnow()
    for sib in rows:
        sib_id = str(sib["id"])
        meta = sib.get("scan_metadata") or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except json.JSONDecodeError:
                meta = {}
        if not isinstance(meta, dict):
            meta = {}

        awaits = str(meta.get("awaits_results_from_scan_id") or "").strip()
        sib_commit = _commit_from_meta(meta)
        sib_branch = _branch_from_config(sib.get("config"))

        linked = awaits == str(winner_scan_id)
        commit_ok = bool(winner_commit and sib_commit and _commits_match(winner_commit, sib_commit))
        branch_ok = (
            not winner_commit
            and not sib_commit
            and winner_branch == sib_branch
        )
        # Pending/running same commit, or cancelled waiting on winner
        status = str(sib.get("status") or "").lower()
        if status == "cancelled" and not linked:
            continue
        if not (linked or commit_ok or branch_ok):
            continue

        meta = dict(meta)
        meta["results_from_scan_id"] = str(winner_scan_id)
        meta["dedupe_promoted_at"] = now.isoformat() + "Z"
        meta.pop("awaits_results_from_scan_id", None)

        try:
            async with database_adapter.get_session() as session:
                await session.execute(
                    text(
                        """
                        UPDATE scans
                        SET status = 'completed',
                            completed_at = :completed_at,
                            updated_at = :updated_at,
                            error_message = NULL,
                            total_vulnerabilities = :total_vulnerabilities,
                            critical_vulnerabilities = :critical_vulnerabilities,
                            high_vulnerabilities = :high_vulnerabilities,
                            medium_vulnerabilities = :medium_vulnerabilities,
                            low_vulnerabilities = :low_vulnerabilities,
                            info_vulnerabilities = :info_vulnerabilities,
                            duration = :duration,
                            results = CAST(:results AS jsonb),
                            scan_metadata = CAST(:metadata AS jsonb)
                        WHERE id = :scan_id
                          AND status IN ('pending', 'running', 'cancelled')
                        """
                    ),
                    {
                        "scan_id": sib_id,
                        "completed_at": now,
                        "updated_at": now,
                        "total_vulnerabilities": vuln_counts.get("total_vulnerabilities", 0),
                        "critical_vulnerabilities": vuln_counts.get("critical_vulnerabilities", 0),
                        "high_vulnerabilities": vuln_counts.get("high_vulnerabilities", 0),
                        "medium_vulnerabilities": vuln_counts.get("medium_vulnerabilities", 0),
                        "low_vulnerabilities": vuln_counts.get("low_vulnerabilities", 0),
                        "info_vulnerabilities": vuln_counts.get("info_vulnerabilities", 0),
                        "duration": duration_seconds,
                        "results": results_json,
                        "metadata": json.dumps(meta),
                    },
                )
                await session.commit()
            _symlink_results(str(winner_scan_id), sib_id)
            try:
                await publish_events(
                    scan_id=sib_id,
                    status="completed",
                    user_id=str(user_id),
                    guest_session_id=meta.get("session_id"),
                    logger=logger,
                )
            except Exception:
                pass
            # Best-effort: ask worker to stop if still running
            try:
                import httpx

                worker_url = os.environ.get("WORKER_URL") or os.environ.get(
                    "SCANNER_WORKER_URL", "http://worker:8001"
                )
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(f"{worker_url}/api/jobs/cancel/{sib_id}")
            except Exception:
                pass
            promoted += 1
            logger.info(
                "Dedupe fanout: promoted sibling %s from winner %s",
                sib_id,
                winner_scan_id,
            )
        except Exception as e:
            logger.warning("Dedupe fanout failed for sibling %s: %s", sib_id, e)

    return promoted


async def try_short_circuit_duplicate_job(
    database_adapter: Any,
    scan_id: str,
    *,
    publish_events,
) -> bool:
    """
    If this scan was cancelled as duplicate, or a completed scan already exists
    for the same repo+commit, mark completed with results_from and return True
    (caller should skip docker execution).
    """
    from sqlalchemy import text

    async with database_adapter.get_session() as session:
        row = await session.execute(
            text(
                """
                SELECT id, user_id, target_url, status, scan_metadata, config,
                       total_vulnerabilities, critical_vulnerabilities, high_vulnerabilities,
                       medium_vulnerabilities, low_vulnerabilities, info_vulnerabilities,
                       duration, results
                FROM scans WHERE id = :id
                """
            ),
            {"id": scan_id},
        )
        me = row.mappings().first()
        if not me:
            return False

        status = str(me.get("status") or "").lower()
        meta = me.get("scan_metadata") or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except json.JSONDecodeError:
                meta = {}
        if not isinstance(meta, dict):
            meta = {}

        awaits = str(meta.get("awaits_results_from_scan_id") or "").strip()
        if status == "cancelled" and awaits:
            # Winner may still be running — leave cancelled until fanout; skip work.
            logger.info("Skip job %s: cancelled duplicate awaiting %s", scan_id, awaits)
            return True

        if status not in ("pending", "running"):
            return status in ("completed", "cancelled", "failed")

        if not me.get("user_id") or not me.get("target_url"):
            return False

        my_commit = _commit_from_meta(meta)
        winner = await session.execute(
            text(
                """
                SELECT id, scan_metadata, total_vulnerabilities, critical_vulnerabilities,
                       high_vulnerabilities, medium_vulnerabilities, low_vulnerabilities,
                       info_vulnerabilities, duration, results
                FROM scans
                WHERE user_id = :user_id
                  AND target_url = :target_url
                  AND status = 'completed'
                  AND id <> :me
                ORDER BY completed_at DESC NULLS LAST, created_at DESC
                LIMIT 20
                """
            ),
            {
                "user_id": me["user_id"],
                "target_url": me["target_url"],
                "me": me["id"],
            },
        )
        for w in winner.mappings().all():
            w_commit = _commit_from_meta(w.get("scan_metadata"))
            if my_commit and w_commit and not _commits_match(my_commit, w_commit):
                continue
            if my_commit and not w_commit:
                continue
            if not my_commit and w_commit:
                # Accept latest completed same URL when we have no commit yet
                pass
            elif not my_commit and not w_commit:
                pass

            # Found a reusable completed scan
            wid = str(w["id"])
            new_meta = dict(meta)
            new_meta["results_from_scan_id"] = wid
            new_meta["dedupe_short_circuit"] = True
            now = datetime.utcnow()
            results_val = w.get("results")
            if results_val is not None and not isinstance(results_val, str):
                results_val = json.dumps(results_val)
            await session.execute(
                text(
                    """
                    UPDATE scans
                    SET status = 'completed',
                        completed_at = :completed_at,
                        updated_at = :updated_at,
                        total_vulnerabilities = :total_vulnerabilities,
                        critical_vulnerabilities = :critical_vulnerabilities,
                        high_vulnerabilities = :high_vulnerabilities,
                        medium_vulnerabilities = :medium_vulnerabilities,
                        low_vulnerabilities = :low_vulnerabilities,
                        info_vulnerabilities = :info_vulnerabilities,
                        duration = :duration,
                        results = CAST(:results AS jsonb),
                        scan_metadata = CAST(:metadata AS jsonb)
                    WHERE id = :scan_id
                    """
                ),
                {
                    "scan_id": scan_id,
                    "completed_at": now,
                    "updated_at": now,
                    "total_vulnerabilities": w.get("total_vulnerabilities") or 0,
                    "critical_vulnerabilities": w.get("critical_vulnerabilities") or 0,
                    "high_vulnerabilities": w.get("high_vulnerabilities") or 0,
                    "medium_vulnerabilities": w.get("medium_vulnerabilities") or 0,
                    "low_vulnerabilities": w.get("low_vulnerabilities") or 0,
                    "info_vulnerabilities": w.get("info_vulnerabilities") or 0,
                    "duration": w.get("duration"),
                    "results": results_val,
                    "metadata": json.dumps(new_meta),
                },
            )
            await session.commit()
            _symlink_results(wid, str(scan_id))
            await publish_events(
                scan_id=str(scan_id),
                status="completed",
                user_id=str(me["user_id"]),
                guest_session_id=new_meta.get("session_id"),
                logger=logger,
            )
            logger.info("Short-circuit scan %s → results from %s", scan_id, wid)
            return True

    return False
