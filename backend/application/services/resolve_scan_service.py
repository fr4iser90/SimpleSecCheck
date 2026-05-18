"""
Resolve scan for automation: return findings when repo HEAD matches last scan, else enqueue scan.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from domain.entities.scan import ScanStatus
from domain.entities.scan_target import ScanTarget
from domain.entities.github_repo import GitHubRepo
from domain.entities.target_type import TargetType
from domain.utils.git_repo_url import normalize_git_repo_url, repo_urls_match
from domain.utils.git_remote import resolve_branch_head_sha
from application.helpers.periodic_repo_scan import commit_hash_from_scan_metadata
from application.helpers.findings_response import build_findings_response
from application.helpers.repo_scan_helper import create_repo_scan
from application.helpers.target_scan_helper import create_scan_from_target
from domain.exceptions.scan_exceptions import ScanValidationException

logger = logging.getLogger(__name__)

@dataclass
class ResolveScanResult:
    """Outcome for POST /api/v1/resolve-scan."""

    status: str  # ready | scanning | started
    scan_id: str
    repo_url: str
    branch: str
    message: str
    commit_sha: Optional[str] = None
    target_id: Optional[str] = None
    github_repo_id: Optional[str] = None
    findings_response: Optional[Any] = None  # ScanFindingsResponseSchema when ready
    progress: Optional[float] = None


def _status_str(scan: Any) -> str:
    s = getattr(scan, "status", None)
    return (getattr(s, "value", s) or "unknown").lower()


def _branch_from_target(target: ScanTarget, fallback: str) -> str:
    cfg = target.config if isinstance(target.config, dict) else {}
    b = cfg.get("branch") or cfg.get("git_branch")
    return str(b).strip() if b else fallback


class ResolveScanService:
    """Agent-oriented resolve: findings or start scan."""

    async def resolve(
        self,
        user_id: str,
        repo_url: str,
        *,
        branch: Optional[str] = None,
        check_commit: bool = True,
        force_scan: bool = False,
        actor_role: str = "user",
        findings_limit: Optional[int] = None,
        findings_offset: int = 0,
        findings_severity: Optional[str] = None,
    ) -> ResolveScanResult:
        from infrastructure.container import (
            get_scan_repository,
            get_scan_target_repository,
            get_github_repo_service,
            get_scan_service,
        )

        normalized = normalize_git_repo_url(repo_url.strip())
        if not normalized:
            raise ScanValidationException("repo_url is required")

        scan_repo = get_scan_repository()
        target_repo = get_scan_target_repository()
        github_svc = get_github_repo_service()
        scan_service = get_scan_service()

        target: Optional[ScanTarget] = None
        gh_repo: Optional[GitHubRepo] = None

        targets = await target_repo.list_by_user(user_id, target_type=TargetType.GIT_REPO.value)
        for t in targets:
            if repo_urls_match(t.source, normalized):
                target = t
                break

        gh_repo = await github_svc.get_by_user_and_url(user_id, normalized)
        if not gh_repo:
            for r in await github_svc.list_by_user(user_id):
                if repo_urls_match(r.repo_url, normalized):
                    gh_repo = r
                    break

        resolved_branch = (branch or "").strip() or None
        if target:
            resolved_branch = resolved_branch or _branch_from_target(target, "main")
        elif gh_repo:
            resolved_branch = resolved_branch or (gh_repo.branch or "main")
        else:
            resolved_branch = resolved_branch or "main"

        canonical_url = target.source if target else (gh_repo.repo_url if gh_repo else normalized)

        active = await scan_repo.find_active_scan_by_user_and_target(user_id, canonical_url)
        if active:
            sid = str(active.id)
            progress = None
            try:
                st = await scan_service.get_scan_status(sid)
                progress = st.get("progress")
            except Exception:
                pass
            return ResolveScanResult(
                status="scanning",
                scan_id=sid,
                repo_url=canonical_url,
                branch=resolved_branch,
                commit_sha=None,
                target_id=target.id if target else None,
                github_repo_id=gh_repo.id if gh_repo else None,
                message="Scan already in progress",
                progress=progress,
            )

        head_sha: Optional[str] = None
        if check_commit and not force_scan:
            head_sha = resolve_branch_head_sha(canonical_url, resolved_branch)

        last = await scan_repo.find_latest_finished_scan_by_user_and_target(
            user_id, canonical_url
        )

        if last and not force_scan:
            last_status = _status_str(last)
            if last_status == ScanStatus.COMPLETED.value:
                last_commit = commit_hash_from_scan_metadata(
                    getattr(last, "metadata", None) or {}
                )
                sha_matches = bool(
                    head_sha
                    and last_commit
                    and head_sha.lower() == last_commit.lower()
                )
                sha_stale = bool(
                    check_commit
                    and head_sha
                    and last_commit
                    and not sha_matches
                )
                if sha_stale:
                    logger.info(
                        "Resolve: HEAD %s differs from last scan %s; starting new scan",
                        head_sha[:8] if head_sha else "?",
                        last_commit[:8] if last_commit else "?",
                    )
                else:
                    dto = await scan_service.get_scan_by_id(str(last.id))
                    findings = build_findings_response(
                        str(last.id),
                        dto,
                        status_str=last_status,
                        limit=findings_limit,
                        offset=findings_offset,
                        severity=findings_severity,
                    )
                    if findings:
                        msg = "Findings are up to date for the current branch HEAD"
                        if check_commit and not head_sha:
                            msg = (
                                "Returning latest findings (remote HEAD could not be resolved; "
                                "commit check skipped)"
                            )
                        elif not check_commit:
                            msg = "Returning latest completed scan findings"
                        return ResolveScanResult(
                            status="ready",
                            scan_id=str(last.id),
                            repo_url=canonical_url,
                            branch=resolved_branch,
                            commit_sha=head_sha or last_commit,
                            target_id=target.id if target else None,
                            github_repo_id=gh_repo.id if gh_repo else None,
                            message=msg,
                            findings_response=findings,
                        )
                    logger.info(
                        "Resolve: completed scan %s has no findings file yet; starting new scan",
                        last.id,
                    )

        scan_id = await self._start_scan(
            user_id=user_id,
            canonical_url=canonical_url,
            branch=resolved_branch,
            target=target,
            gh_repo=gh_repo,
            head_sha=head_sha,
            actor_role=actor_role,
        )

        return ResolveScanResult(
            status="started",
            scan_id=scan_id,
            repo_url=canonical_url,
            branch=resolved_branch,
            commit_sha=head_sha,
            target_id=target.id if target else None,
            github_repo_id=gh_repo.id if gh_repo else None,
            message="Scan queued; poll GET /api/v1/scans/{scan_id}/status until completed, then GET .../findings",
        )

    async def _start_scan(
        self,
        *,
        user_id: str,
        canonical_url: str,
        branch: str,
        target: Optional[ScanTarget],
        gh_repo: Optional[GitHubRepo],
        head_sha: Optional[str],
        actor_role: str,
    ) -> str:
        meta = {
            "trigger": "resolve_scan_api",
            "requested_branch": branch,
        }
        if head_sha:
            meta["commit_hash"] = head_sha

        if target:
            if branch:
                from application.helpers.target_scan_helper import create_scan_from_target

                sid = await create_scan_from_target(
                    target,
                    metadata_extra=meta,
                    config_override={"branch": branch, "git_branch": branch},
                    enforcement_mode="full",
                )
            else:
                from application.services.scan_target_service import ScanTargetService
                from infrastructure.container import get_scan_target_repository

                svc = ScanTargetService(get_scan_target_repository())
                sid = await svc.trigger_scan(
                    target.id,
                    user_id,
                    metadata_extra=meta,
                    enforcement_mode="full",
                )
            if not sid:
                raise ScanValidationException("Failed to start scan for target")
            return sid

        if gh_repo:
            sid = await create_repo_scan(
                repo_url=gh_repo.repo_url,
                repo_name=gh_repo.repo_name,
                branch=branch or gh_repo.branch,
                user_id=user_id,
                scanners=gh_repo.scanners,
                commit_hash=head_sha,
                metadata={**meta, "repo_id": gh_repo.id},
            )
            if not sid:
                raise ScanValidationException("Failed to start scan for repository")
            return sid

        sid = await create_repo_scan(
            repo_url=canonical_url,
            repo_name=canonical_url.rstrip("/").split("/")[-1].replace(".git", ""),
            branch=branch,
            user_id=user_id,
            commit_hash=head_sha,
            metadata=meta,
        )
        if not sid:
            raise ScanValidationException(
                "Failed to start scan (register repo under My Repos or My Targets for recurring use)"
            )
        return sid
