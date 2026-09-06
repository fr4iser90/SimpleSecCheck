"""
Collapse duplicate active scans for the same user + git repo (+ commit).

Keeps one winner (running preferred, else oldest). Others are cancelled, dequeued,
and tagged with awaits_results_from_scan_id so completion can promote them to
completed with shared findings.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from application.helpers.periodic_repo_scan import (
    commit_hash_from_scan_metadata,
    commits_match,
    scan_metadata_dict,
)
from domain.datetime_serialization import isoformat_utc
from domain.entities.scan import Scan, ScanStatus

logger = logging.getLogger(__name__)


def _status_val(scan: Scan) -> str:
    s = getattr(scan, "status", None)
    return str(getattr(s, "value", s) or "").lower()


def _branch_key(scan: Scan) -> str:
    cfg = getattr(scan, "config", None) or {}
    if not isinstance(cfg, dict):
        return ""
    b = cfg.get("git_branch") or cfg.get("branch") or ""
    return str(b).strip().lower()


def dedupe_group_key(scan: Scan) -> Tuple[str, str]:
    """
    Group key: (target_url, commit_or_branch).

    Same repo + matching commit collapse together. If commit unknown, same branch
    on the same URL is treated as one group (typical bulk 'scan all' duplicates).
    """
    url = (getattr(scan, "target_url", None) or "").strip().lower()
    commit = commit_hash_from_scan_metadata(scan_metadata_dict(scan))
    if commit:
        # Normalize to lowercase full/prefix-friendly token
        return url, f"c:{commit.lower()}"
    return url, f"b:{_branch_key(scan) or 'default'}"


def groups_match(a: Scan, b: Scan) -> bool:
    """True when two active scans are duplicates for dedupe purposes."""
    url_a = (getattr(a, "target_url", None) or "").strip().lower()
    url_b = (getattr(b, "target_url", None) or "").strip().lower()
    if not url_a or url_a != url_b:
        return False
    ca = commit_hash_from_scan_metadata(scan_metadata_dict(a))
    cb = commit_hash_from_scan_metadata(scan_metadata_dict(b))
    if ca and cb:
        return commits_match(ca, cb)
    if ca or cb:
        # One known commit: still merge if same branch (ls-remote pending on the other)
        return _branch_key(a) == _branch_key(b)
    return _branch_key(a) == _branch_key(b)


def pick_winner(scans: List[Scan], *, keep_scan_id: Optional[str] = None) -> Optional[Scan]:
    if not scans:
        return None
    if keep_scan_id:
        for s in scans:
            if str(s.id) == str(keep_scan_id):
                return s
    running = [s for s in scans if _status_val(s) == ScanStatus.RUNNING.value]
    pool = running or scans

    def _created(s: Scan) -> datetime:
        return getattr(s, "created_at", None) or datetime.utcnow()

    return sorted(pool, key=_created)[0]


async def collapse_duplicate_group(
    *,
    scan_repository: Any,
    queue_service: Any,
    scans: List[Scan],
    keep_scan_id: Optional[str] = None,
) -> Optional[Scan]:
    """Cancel+dequeue all but the winner in a duplicate group. Returns winner."""
    if len(scans) <= 1:
        return scans[0] if scans else None

    winner = pick_winner(scans, keep_scan_id=keep_scan_id)
    if not winner:
        return None

    for scan in scans:
        if str(scan.id) == str(winner.id):
            continue
        if _status_val(scan) not in (
            ScanStatus.PENDING.value,
            ScanStatus.RUNNING.value,
        ):
            continue
        try:
            meta = dict(scan.scan_metadata or {})
            meta["awaits_results_from_scan_id"] = str(winner.id)
            meta["deduped_as_duplicate"] = True
            meta["cancellation_reason"] = "duplicate_same_repo_commit"
            meta["cancelled_at"] = isoformat_utc(datetime.utcnow())
            scan.scan_metadata = meta
            scan.cancel()
            await scan_repository.update(scan)
            try:
                await queue_service.cancel_scan(str(scan.id))
            except Exception as qe:
                logger.warning("Dedupe: queue cancel failed for %s: %s", scan.id, qe)
            logger.info(
                "Dedupe: cancelled duplicate scan %s → awaits %s (%s)",
                scan.id,
                winner.id,
                (scan.target_url or "")[:80],
            )
        except Exception as e:
            logger.warning("Dedupe: failed to cancel scan %s: %s", scan.id, e)
    return winner


async def collapse_active_duplicates_for_target(
    *,
    scan_repository: Any,
    queue_service: Any,
    user_id: str,
    target_url: str,
    keep_scan_id: Optional[str] = None,
) -> Optional[Scan]:
    """Collapse duplicate active scans for one user+target URL. Returns preferred winner."""
    actives = await scan_repository.find_active_scans_by_user_and_target(
        user_id, target_url
    )
    if not actives:
        return None
    # Exact URL preferred
    wanted = (target_url or "").strip().lower()
    exact = [
        s
        for s in actives
        if (getattr(s, "target_url", None) or "").strip().lower() == wanted
    ]
    pool = exact or actives
    if len(pool) <= 1:
        return pool[0] if pool else None

    # Split into commit/branch groups
    buckets: Dict[Tuple[str, str], List[Scan]] = defaultdict(list)
    for s in pool:
        buckets[dedupe_group_key(s)].append(s)

    # Also merge buckets that match via commits_match / same branch heuristics
    # (prefix SHA vs full SHA land in different c: keys)
    merged: List[List[Scan]] = []
    for group in buckets.values():
        placed = False
        for existing in merged:
            if groups_match(existing[0], group[0]):
                existing.extend(group)
                placed = True
                break
        if not placed:
            merged.append(list(group))

    winner_out: Optional[Scan] = None
    for group in merged:
        w = await collapse_duplicate_group(
            scan_repository=scan_repository,
            queue_service=queue_service,
            scans=group,
            keep_scan_id=keep_scan_id,
        )
        if w and keep_scan_id and str(w.id) == str(keep_scan_id):
            winner_out = w
        elif w and winner_out is None:
            winner_out = w
    return winner_out


async def collapse_all_active_duplicates_for_user(
    *,
    scan_repository: Any,
    queue_service: Any,
    user_id: str,
) -> int:
    """
    Sweep all pending/running scans for a user and collapse duplicate groups.
    Returns number of cancelled duplicates.
    """
    from domain.entities.scan import ScanStatus as SS

    pending = await scan_repository.get_by_status(SS.PENDING, limit=2000)
    running = await scan_repository.get_by_status(SS.RUNNING, limit=2000)
    mine = [
        s
        for s in (pending + running)
        if str(getattr(s, "user_id", None) or "") == str(user_id)
    ]
    if len(mine) <= 1:
        return 0

    buckets: Dict[Tuple[str, str], List[Scan]] = defaultdict(list)
    for s in mine:
        buckets[dedupe_group_key(s)].append(s)

    merged: List[List[Scan]] = []
    for group in buckets.values():
        placed = False
        for existing in merged:
            if groups_match(existing[0], group[0]):
                existing.extend(group)
                placed = True
                break
        if not placed:
            merged.append(list(group))

    cancelled = 0
    for group in merged:
        if len(group) <= 1:
            continue
        before = {str(s.id) for s in group}
        winner = await collapse_duplicate_group(
            scan_repository=scan_repository,
            queue_service=queue_service,
            scans=group,
        )
        if winner:
            cancelled += len(before) - 1
    return cancelled
