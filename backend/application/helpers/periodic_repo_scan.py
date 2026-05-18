"""
Periodic GitHub repo scan eligibility (scan_frequency + commit SHA diff).

Used by AutoScanScheduler and AutoScanService.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from domain.entities.github_repo import GitHubRepo
from domain.entities.repo_scan_history_entry import RepoScanHistoryEntry
from domain.utils.git_remote import resolve_branch_head_sha

# Minimum time between any scans for the same repo (avoids double-scan after webhook push).
DEFAULT_PERIODIC_COOLDOWN_SECONDS = 7200  # 2 hours

_FREQUENCY_MIN_INTERVAL = {
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
}


def _utcnow() -> datetime:
    return datetime.utcnow()


def _naive(dt: datetime) -> datetime:
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def periodic_frequency_supports_scheduler(frequency: str) -> bool:
    """True when scan_frequency should be driven by the periodic scheduler tick."""
    return (frequency or "").lower() in _FREQUENCY_MIN_INTERVAL


def frequency_interval_elapsed(
    scan_frequency: str,
    last_scan_at: datetime,
    *,
    now: Optional[datetime] = None,
) -> bool:
    """True if enough time has passed since last_scan_at for daily/weekly."""
    freq = (scan_frequency or "").lower()
    min_delta = _FREQUENCY_MIN_INTERVAL.get(freq)
    if not min_delta:
        return False
    now = _naive(now or _utcnow())
    last = _naive(last_scan_at)
    return (now - last) >= min_delta


def cooldown_blocks_scan(
    last_scan_at: datetime,
    *,
    cooldown_seconds: int = DEFAULT_PERIODIC_COOLDOWN_SECONDS,
    now: Optional[datetime] = None,
) -> bool:
    """True if a scan completed too recently (e.g. right after a push webhook)."""
    if cooldown_seconds <= 0:
        return False
    now = _naive(now or _utcnow())
    last = _naive(last_scan_at)
    return (now - last).total_seconds() < cooldown_seconds


def commit_hash_from_scan_metadata(metadata: Optional[Dict[str, Any]]) -> Optional[str]:
    """Extract last known commit from scan metadata (repo scans / webhooks)."""
    if not isinstance(metadata, dict):
        return None
    raw = metadata.get("commit_hash") or metadata.get("commit")
    if raw:
        return str(raw).strip() or None
    git_info = metadata.get("git_info")
    if isinstance(git_info, dict):
        gh = git_info.get("commit_hash") or git_info.get("commit")
        if gh:
            return str(gh).strip() or None
    return None


def history_entry_from_scan(
    repo_id: str,
    *,
    scan_id: str,
    branch: Optional[str],
    commit_hash: Optional[str],
    created_at: datetime,
) -> RepoScanHistoryEntry:
    """Build a history-shaped entry from a finished scan row."""
    return RepoScanHistoryEntry(
        id=scan_id,
        repo_id=repo_id,
        scan_id=scan_id,
        branch=branch,
        commit_hash=commit_hash,
        score=None,
        vulnerabilities={},
        created_at=created_at,
    )


def commit_unchanged(
    repo: GitHubRepo,
    last_entry: RepoScanHistoryEntry,
    *,
    head_sha: Optional[str] = None,
) -> bool:
    """
    True when remote branch HEAD matches last recorded commit (skip rescan).

    If head cannot be resolved, returns False (caller may still scan).
    """
    last_sha = (last_entry.commit_hash or "").strip()
    if not last_sha:
        return False
    if head_sha is None:
        head_sha = resolve_branch_head_sha(repo.repo_url, repo.branch)
    if not head_sha:
        return False
    return head_sha.strip().lower() == last_sha.lower()


def evaluate_periodic_repo_scan(
    repo: GitHubRepo,
    last_entry: Optional[RepoScanHistoryEntry],
    *,
    cooldown_seconds: int = DEFAULT_PERIODIC_COOLDOWN_SECONDS,
    now: Optional[datetime] = None,
) -> Tuple[bool, str, Optional[str]]:
    """
    Decide whether a repo should get a periodic scheduler scan.

    Returns:
        (should_scan, reason, resolved_head_sha)
    """
    if not repo.auto_scan_enabled:
        return False, "auto_scan_disabled", None

    freq = (repo.scan_frequency or "on_push").lower()

    if freq == "manual":
        return False, "manual_only", None

    if freq == "on_push":
        return False, "on_push_webhook_only", None

    if not periodic_frequency_supports_scheduler(freq):
        return False, f"unsupported_frequency:{freq}", None

    if not last_entry or not last_entry.created_at:
        return False, "no_scan_history_use_initial_scheduler", None

    last_at = last_entry.created_at

    if cooldown_blocks_scan(last_at, cooldown_seconds=cooldown_seconds, now=now):
        return False, "cooldown_after_recent_scan", None

    if not frequency_interval_elapsed(freq, last_at, now=now):
        return False, f"interval_not_elapsed:{freq}", None

    head_sha = resolve_branch_head_sha(repo.repo_url, repo.branch)
    if commit_unchanged(repo, last_entry, head_sha=head_sha):
        return False, "no_new_commit", head_sha

    return True, f"due:{freq}", head_sha
