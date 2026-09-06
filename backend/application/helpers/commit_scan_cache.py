"""
Commit-based scan reuse: same user + git target + commit → return existing scan.

Used by ScanService.create_scan so API keys, resolve-scan, web "Scan now",
webhooks, and schedulers all share one cache path. There is no force bypass.
"""
from __future__ import annotations

import logging
from typing import Any, Optional, Tuple

from application.helpers.findings_file import load_findings_payload
from application.helpers.periodic_repo_scan import (
    commit_hash_from_scan_metadata,
    commits_match,
)
from domain.entities.scan import Scan, ScanStatus
from domain.entities.target_type import TargetType
from domain.utils.git_remote import resolve_branch_head_sha

logger = logging.getLogger(__name__)


def is_git_repo_scan_request(*, target_type: Optional[str], target_url: Optional[str]) -> bool:
    tt = (target_type or "").strip().lower()
    if tt == TargetType.GIT_REPO.value:
        return True
    url = (target_url or "").strip().lower()
    if not url:
        return False
    return (
        url.startswith("http://")
        or url.startswith("https://")
        or url.startswith("git@")
        or url.endswith(".git")
    )


def branch_from_scan_config(config: Optional[dict]) -> str:
    if not isinstance(config, dict):
        return "main"
    b = config.get("git_branch") or config.get("branch")
    return str(b).strip() if b else "main"


def normalize_commit_into_metadata(metadata: Optional[dict], commit_sha: Optional[str]) -> dict:
    """Ensure commit_hash is set; drop redundant commit_sha once normalized."""
    meta = dict(metadata or {})
    existing = commit_hash_from_scan_metadata(meta)
    sha = (commit_sha or existing or "").strip() or None
    if sha:
        meta["commit_hash"] = sha
        if "commit_sha" in meta and commits_match(meta.get("commit_sha"), sha):
            # Keep one canonical key for extractors / SQL later.
            meta.pop("commit_sha", None)
    return meta


def resolve_commit_for_git_request(
    *,
    target_url: str,
    config: Optional[dict],
    metadata: Optional[dict],
    check_remote: bool = True,
) -> Tuple[Optional[str], dict]:
    """
    Resolve commit SHA for a git scan request and return (sha, updated_metadata).

    Prefers metadata commit; optionally falls back to git ls-remote HEAD.
    """
    meta = normalize_commit_into_metadata(metadata, None)
    commit = commit_hash_from_scan_metadata(meta)
    if commit:
        return commit, meta
    if not check_remote:
        return None, meta
    branch = branch_from_scan_config(config)
    head = resolve_branch_head_sha(target_url, branch)
    if head:
        meta = normalize_commit_into_metadata(meta, head)
        return head, meta
    return None, meta


def completed_scan_has_reusable_results(scan_id: str) -> bool:
    """True when findings payload exists (including empty findings list)."""
    _payload, source = load_findings_payload(scan_id)
    return source != "missing"


async def find_reusable_scan_for_commit(
    scan_repository: Any,
    *,
    user_id: str,
    target_url: str,
    commit_sha: str,
) -> Optional[Scan]:
    """Return a completed scan for this commit when results are still on disk."""
    scan = await scan_repository.find_completed_scan_by_user_target_and_commit(
        user_id, target_url, commit_sha
    )
    if not scan:
        return None
    status = getattr(scan.status, "value", scan.status)
    if str(status).lower() != ScanStatus.COMPLETED.value:
        return None
    if not completed_scan_has_reusable_results(str(scan.id)):
        logger.info(
            "Commit cache: completed scan %s for %s has no findings file; not reusing",
            scan.id,
            (commit_sha or "")[:8],
        )
        return None
    return scan


async def find_active_scan_for_target(
    scan_repository: Any,
    *,
    user_id: str,
    target_url: str,
) -> Optional[Scan]:
    """Join an in-flight scan for the same user+target instead of enqueueing another."""
    active = await scan_repository.find_active_scan_by_user_and_target(user_id, target_url)
    if not active:
        return None
    # Prefer exact target_url match when contains-search is loose.
    active_url = (getattr(active, "target_url", None) or "").strip()
    wanted = (target_url or "").strip()
    if active_url and wanted and active_url != wanted:
        # Still accept if one contains the other (legacy helper behavior).
        if wanted not in active_url and active_url not in wanted:
            return None
    return active
