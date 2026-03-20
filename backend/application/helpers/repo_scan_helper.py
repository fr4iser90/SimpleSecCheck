"""
Repository Scan Helper

Helper functions for creating scans for GitHub repositories.
"""
from typing import Optional, Dict, Any
import logging

from domain.entities.scan import ScanType
from domain.entities.target_type import TargetType
from application.dtos.request_dto import ScanRequestDTO
from application.services.scan_service import ScanService

logger = logging.getLogger(__name__)


async def create_repo_scan(
    repo_url: str,
    repo_name: str,
    branch: str,
    user_id: str,
    commit_hash: Optional[str] = None,
    scanners: Optional[list[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """Create a scan for a GitHub repository."""
    try:
        if scanners is None:
            from infrastructure.container import get_scanner_repository
            repo = get_scanner_repository()
            all_scanners = await repo.list_all()
            code_scanners = [
                s.name for s in all_scanners
                if s.enabled and s.scan_types and "code" in [st.lower() for st in s.scan_types]
            ]
            ordered = sorted(
                [s for s in all_scanners if s.name in code_scanners],
                key=lambda x: -x.priority,
            )
            code_scanners = [s.name for s in ordered]
            if not code_scanners:
                raise ValueError("No code scanners found in database. Please ensure scanners are discovered.")
            scanners = code_scanners
            logger.info("Using %s code scanners from database for repo %s: %s", len(scanners), repo_name, ", ".join(scanners))

        scan_name = f"Scan: {repo_name} ({branch})"
        if commit_hash:
            scan_name += f" @ {commit_hash[:8]}"

        description = f"Automated scan for {repo_url} on branch {branch}"
        if commit_hash:
            description += f" at commit {commit_hash}"

        config = {
            "git_branch": branch,
            "target_mount_path": None
        }

        scan_metadata = {
            "repo_url": repo_url,
            "repo_name": repo_name,
            "branch": branch,
            "source": "auto_scan",
            **(metadata or {})
        }
        if commit_hash:
            scan_metadata["commit_hash"] = commit_hash

        scan_request = ScanRequestDTO(
            name=scan_name,
            description=description,
            scan_type=ScanType.CODE,
            target_url=repo_url,
            target_type=TargetType.GIT_REPO.value,
            user_id=user_id,
            scanners=scanners,
            config=config,
            metadata=scan_metadata,
            tags=["auto-scan", "github-repo"]
        )

        from infrastructure.container import get_scan_service
        scan_service: ScanService = get_scan_service()
        scan_dto = await scan_service.create_scan(scan_request)
        logger.info("Created scan %s for repository %s (branch: %s)", scan_dto.id, repo_url, branch)
        return scan_dto.id

    except Exception as e:
        logger.error("Failed to create scan for repository %s: %s", repo_url, e, exc_info=True)
        return None
