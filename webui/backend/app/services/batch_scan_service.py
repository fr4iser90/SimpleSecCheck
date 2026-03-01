"""
Batch Scan Service
Handles bulk repository scanning:
- Queue management for multiple repositories
- Progress tracking per repository
- Sequential or parallel scanning (sequential for now)
- Aggregated results collection
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel
from fastapi import HTTPException

from .scan_service import ScanRequest, start_scan, get_scan_status, stop_scan
from .git_service import is_git_url


class BatchScanStatus(str, Enum):
    """Batch scan status"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class RepositoryScanStatus(str, Enum):
    """Individual repository scan status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class RepositoryScan(BaseModel):
    """Information about a single repository scan"""
    repository_url: str
    repository_name: str
    status: RepositoryScanStatus = RepositoryScanStatus.PENDING
    scan_id: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error_message: Optional[str] = None
    results_dir: Optional[str] = None
    findings_count: Optional[int] = None


class BatchScanRequest(BaseModel):
    """Request to start a batch scan"""
    scan_type: str  # code, website, network
    repositories: List[str]  # List of repository URLs
    git_branch: Optional[str] = None
    ci_mode: bool = False
    finding_policy: Optional[str] = None
    collect_metadata: bool = False


class BatchScanProgress(BaseModel):
    """Progress information for a batch scan"""
    batch_id: str
    status: BatchScanStatus
    total_repos: int
    completed_repos: int
    failed_repos: int
    skipped_repos: int
    current_repo: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    repositories: List[RepositoryScan] = []


# Global batch scan state (in-memory, no DB)
_current_batch_scan: Optional[Dict[str, Any]] = None
_batch_scan_lock = asyncio.Lock()


def generate_batch_id() -> str:
    """Generate a unique batch scan ID"""
    return datetime.now().strftime("batch_%Y%m%d_%H%M%S")


async def start_batch_scan(
    request: BatchScanRequest,
    base_dir: Path,
    results_dir: Path,
    cli_script: Path
) -> BatchScanProgress:
    """
    Start a batch scan for multiple repositories.
    
    Args:
        request: Batch scan request with repository list
        base_dir: Base directory for the webui
        results_dir: Results directory
        cli_script: CLI script path (not used, but kept for compatibility)
    
    Returns:
        Batch scan progress information
    """
    global _current_batch_scan
    
    async with _batch_scan_lock:
        # Check if batch scan is already running
        if _current_batch_scan and _current_batch_scan.get("status") == BatchScanStatus.RUNNING:
            raise HTTPException(status_code=409, detail="Batch scan already running")
        
        # Validate scan type
        if request.scan_type not in ["code", "website", "network"]:
            raise HTTPException(status_code=400, detail="Invalid scan type")
        
        # Validate repositories
        if not request.repositories or len(request.repositories) == 0:
            raise HTTPException(status_code=400, detail="At least one repository is required")
        
        # Filter and validate repository URLs
        valid_repos = []
        for repo_url in request.repositories:
            repo_url = repo_url.strip()
            if not repo_url:
                continue
            
            # For code scans, validate Git URLs
            if request.scan_type == "code" and not is_git_url(repo_url):
                # Skip invalid URLs, but log them
                print(f"[Batch Scan] Skipping invalid Git URL: {repo_url}")
                continue
            
            # Extract repository name
            repo_name = extract_repo_name(repo_url)
            valid_repos.append({
                "url": repo_url,
                "name": repo_name
            })
        
        if len(valid_repos) == 0:
            raise HTTPException(status_code=400, detail="No valid repositories found")
        
        # Create batch scan state
        batch_id = generate_batch_id()
        repositories = [
            RepositoryScan(
                repository_url=repo["url"],
                repository_name=repo["name"],
                status=RepositoryScanStatus.PENDING
            )
            for repo in valid_repos
        ]
        
        _current_batch_scan = {
            "batch_id": batch_id,
            "status": BatchScanStatus.RUNNING,
            "scan_type": request.scan_type,
            "git_branch": request.git_branch,
            "ci_mode": request.ci_mode,
            "finding_policy": request.finding_policy,
            "collect_metadata": request.collect_metadata,
            "repositories": repositories,
            "current_index": 0,
            "started_at": datetime.now().isoformat(),
            "finished_at": None,
            "base_dir": base_dir,
            "results_dir": results_dir,
            "cli_script": cli_script,
            "current_scan": None,  # Will hold the current single scan state
        }
        
        # Start background task to process batch
        asyncio.create_task(process_batch_scan(_current_batch_scan))
        
        return get_batch_scan_progress(batch_id)


def extract_repo_name(repo_url: str) -> str:
    """Extract repository name from URL"""
    repo_url = repo_url.strip().rstrip("/")
    
    # GitHub/GitLab HTTPS: https://github.com/user/repo -> repo
    if "github.com" in repo_url or "gitlab.com" in repo_url:
        parts = repo_url.split("/")
        if len(parts) >= 2:
            name = parts[-1].replace(".git", "")
            return name
    
    # SSH: git@github.com:user/repo.git -> repo
    if repo_url.startswith("git@"):
        parts = repo_url.split(":")[-1].replace(".git", "").split("/")
        if len(parts) >= 1:
            return parts[-1]
    
    # Fallback: use last part of URL
    return repo_url.split("/")[-1].replace(".git", "")


async def process_batch_scan(batch_state: Dict[str, Any]) -> None:
    """
    Process batch scan sequentially (one repo at a time).
    This runs in a background task.
    """
    repositories = batch_state["repositories"]
    total = len(repositories)
    
    print(f"[Batch Scan] Starting batch scan {batch_state['batch_id']} with {total} repositories")
    
    for index, repo_scan in enumerate(repositories):
        # Check if batch was stopped
        if batch_state.get("status") == BatchScanStatus.STOPPED:
            repo_scan.status = RepositoryScanStatus.SKIPPED
            continue
        
        # Check if batch was paused
        while batch_state.get("status") == BatchScanStatus.PAUSED:
            await asyncio.sleep(1)
            if batch_state.get("status") == BatchScanStatus.STOPPED:
                repo_scan.status = RepositoryScanStatus.SKIPPED
                break
        
        if batch_state.get("status") == BatchScanStatus.STOPPED:
            continue
        
        # Update current repository
        batch_state["current_index"] = index
        repo_scan.status = RepositoryScanStatus.RUNNING
        repo_scan.started_at = datetime.now().isoformat()
        
        print(f"[Batch Scan] Scanning repository {index + 1}/{total}: {repo_scan.repository_name}")
        
        try:
            # Create scan request for this repository
            scan_request = ScanRequest(
                type=batch_state["scan_type"],
                target=repo_scan.repository_url,
                git_branch=batch_state.get("git_branch"),
                ci_mode=batch_state.get("ci_mode", False),
                finding_policy=batch_state.get("finding_policy"),
                collect_metadata=batch_state.get("collect_metadata", False)
            )
            
            # Create a temporary scan state for this repository
            current_scan = {
                "process": None,
                "status": "idle",
                "scan_id": None,
                "started_at": None,
                "error_code": None,
                "error_message": None,
                "container_ids": [],
                "temp_clone_path": None,
                "step_names": {},
                "step_logs": [],
            }
            
            batch_state["current_scan"] = current_scan
            
            # Start scan
            scan_status = await start_scan(
                scan_request,
                current_scan,
                batch_state["cli_script"],
                batch_state["base_dir"],
                batch_state["results_dir"]
            )
            
            repo_scan.scan_id = scan_status.scan_id
            
            # Wait for scan to complete
            while current_scan["status"] == "running":
                await asyncio.sleep(2)
                # Check scan status
                status = get_scan_status(current_scan)
                if status.status in ["done", "error"]:
                    break
            
            # Get final status
            final_status = get_scan_status(current_scan)
            
            if final_status.status == "done":
                repo_scan.status = RepositoryScanStatus.COMPLETED
                repo_scan.results_dir = final_status.results_dir
                # Try to extract findings count from results
                if final_status.results_dir:
                    findings_count = extract_findings_count(Path(final_status.results_dir))
                    repo_scan.findings_count = findings_count
            else:
                repo_scan.status = RepositoryScanStatus.FAILED
                repo_scan.error_message = final_status.error_message or "Scan failed"
            
            repo_scan.finished_at = datetime.now().isoformat()
            
        except Exception as e:
            repo_scan.status = RepositoryScanStatus.FAILED
            repo_scan.error_message = str(e)
            repo_scan.finished_at = datetime.now().isoformat()
            print(f"[Batch Scan] Error scanning {repo_scan.repository_name}: {e}")
        
        finally:
            # Cleanup current scan state
            batch_state["current_scan"] = None
    
    # Mark batch as completed
    batch_state["status"] = BatchScanStatus.COMPLETED
    batch_state["finished_at"] = datetime.now().isoformat()
    print(f"[Batch Scan] Batch scan {batch_state['batch_id']} completed")


def extract_findings_count(results_dir: Path) -> Optional[int]:
    """Extract findings count from scan results"""
    try:
        # Look for summary JSON file
        summary_file = results_dir / "security-summary.json"
        if summary_file.exists():
            with open(summary_file, "r") as f:
                summary = json.load(f)
                # Try different possible keys
                if "findings" in summary:
                    return len(summary["findings"])
                if "total_findings" in summary:
                    return summary["total_findings"]
                if "summary" in summary and "total" in summary["summary"]:
                    return summary["summary"]["total"]
    except Exception as e:
        print(f"[Batch Scan] Could not extract findings count: {e}")
    
    return None


def get_batch_scan_progress(batch_id: Optional[str] = None) -> Optional[BatchScanProgress]:
    """
    Get progress information for a batch scan.
    If batch_id is None, returns the current batch scan.
    """
    global _current_batch_scan
    
    if not _current_batch_scan:
        return None
    
    if batch_id and _current_batch_scan.get("batch_id") != batch_id:
        return None
    
    batch_state = _current_batch_scan
    repositories = batch_state["repositories"]
    
    completed = sum(1 for r in repositories if r.status == RepositoryScanStatus.COMPLETED)
    failed = sum(1 for r in repositories if r.status == RepositoryScanStatus.FAILED)
    skipped = sum(1 for r in repositories if r.status == RepositoryScanStatus.SKIPPED)
    
    current_repo = None
    current_index = batch_state.get("current_index", 0)
    if 0 <= current_index < len(repositories):
        current_repo_obj = repositories[current_index]
        if current_repo_obj.status == RepositoryScanStatus.RUNNING:
            current_repo = current_repo_obj.repository_name
    
    return BatchScanProgress(
        batch_id=batch_state["batch_id"],
        status=batch_state["status"],
        total_repos=len(repositories),
        completed_repos=completed,
        failed_repos=failed,
        skipped_repos=skipped,
        current_repo=current_repo,
        started_at=batch_state.get("started_at"),
        finished_at=batch_state.get("finished_at"),
        repositories=repositories
    )


async def pause_batch_scan() -> None:
    """Pause the current batch scan"""
    global _current_batch_scan
    
    async with _batch_scan_lock:
        if not _current_batch_scan:
            raise HTTPException(status_code=404, detail="No batch scan running")
        
        if _current_batch_scan["status"] != BatchScanStatus.RUNNING:
            raise HTTPException(status_code=400, detail="Batch scan is not running")
        
        _current_batch_scan["status"] = BatchScanStatus.PAUSED
        print(f"[Batch Scan] Batch scan {_current_batch_scan['batch_id']} paused")


async def resume_batch_scan() -> None:
    """Resume a paused batch scan"""
    global _current_batch_scan
    
    async with _batch_scan_lock:
        if not _current_batch_scan:
            raise HTTPException(status_code=404, detail="No batch scan running")
        
        if _current_batch_scan["status"] != BatchScanStatus.PAUSED:
            raise HTTPException(status_code=400, detail="Batch scan is not paused")
        
        _current_batch_scan["status"] = BatchScanStatus.RUNNING
        print(f"[Batch Scan] Batch scan {_current_batch_scan['batch_id']} resumed")


async def stop_batch_scan() -> None:
    """Stop the current batch scan"""
    global _current_batch_scan
    
    async with _batch_scan_lock:
        if not _current_batch_scan:
            raise HTTPException(status_code=404, detail="No batch scan running")
        
        if _current_batch_scan["status"] == BatchScanStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Batch scan already completed")
        
        # Stop current scan if running
        current_scan = _current_batch_scan.get("current_scan")
        if current_scan and current_scan.get("status") == "running":
            try:
                await stop_scan(current_scan)
            except Exception as e:
                print(f"[Batch Scan] Error stopping current scan: {e}")
        
        _current_batch_scan["status"] = BatchScanStatus.STOPPED
        _current_batch_scan["finished_at"] = datetime.now().isoformat()
        print(f"[Batch Scan] Batch scan {_current_batch_scan['batch_id']} stopped")
