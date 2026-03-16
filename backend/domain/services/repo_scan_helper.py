"""
Repository Scan Helper

Helper functions for creating scans for GitHub repositories.
"""
from typing import Optional, Dict, Any
import logging
from datetime import datetime

from domain.entities.scan import ScanType
from domain.entities.target_type import TargetType
from application.dtos.request_dto import ScanRequestDTO
from application.services.scan_service import ScanService
from infrastructure.container import get_scan_service

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
    """
    Create a scan for a GitHub repository.
    
    Args:
        repo_url: Repository URL (e.g., https://github.com/user/repo)
        repo_name: Repository name for display
        branch: Branch to scan
        user_id: User ID who owns the repository
        commit_hash: Optional commit hash
        scanners: Optional list of scanners to use (defaults to all enabled code scanners from database)
        metadata: Optional metadata to attach to scan
        
    Returns:
        Scan ID if successful, None otherwise
    """
    try:
        # If scanners not provided, get all enabled code scanners from database
        if scanners is None:
            from infrastructure.database.adapter import db_adapter
            from infrastructure.database.models import Scanner
            from sqlalchemy import select
            
            await db_adapter.ensure_initialized()
            async with db_adapter.async_session() as session:
                # Get all enabled scanners that support "code" scan type
                result = await session.execute(
                    select(Scanner)
                    .where(Scanner.enabled == True)
                    .order_by(Scanner.priority.desc())
                )
                db_scanners = result.scalars().all()
                
                # Filter scanners that support "code" scan type
                code_scanners = []
                for scanner in db_scanners:
                    scan_types = scanner.scan_types if isinstance(scanner.scan_types, list) else []
                    if "code" in [st.lower() for st in scan_types]:
                        code_scanners.append(scanner.name)
                
                if not code_scanners:
                    raise ValueError("No code scanners found in database. Please ensure scanners are discovered.")
                
                scanners = code_scanners
                logger.info(f"Using {len(scanners)} code scanners from database for repo {repo_name}: {', '.join(scanners)}")
        
        # Build scan name
        scan_name = f"Scan: {repo_name} ({branch})"
        if commit_hash:
            scan_name += f" @ {commit_hash[:8]}"
        
        # Build scan description
        description = f"Automated scan for {repo_url} on branch {branch}"
        if commit_hash:
            description += f" at commit {commit_hash}"
        
        # Build config with git branch
        config = {
            "git_branch": branch,
            "target_mount_path": None  # Will be cloned by worker
        }
        
        # Build metadata
        scan_metadata = {
            "repo_url": repo_url,
            "repo_name": repo_name,
            "branch": branch,
            "source": "auto_scan",
            **(metadata or {})
        }
        if commit_hash:
            scan_metadata["commit_hash"] = commit_hash
        
        # Create scan request
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
        
        # Get scan service and create scan
        scan_service = get_scan_service()
        scan_dto = await scan_service.create_scan(scan_request)
        
        logger.info(f"Created scan {scan_dto.id} for repository {repo_url} (branch: {branch})")
        return scan_dto.id
        
    except Exception as e:
        logger.error(f"Failed to create scan for repository {repo_url}: {e}", exc_info=True)
        return None
