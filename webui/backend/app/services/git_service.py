"""
Git Service
Handles Git repository operations (cloning, URL detection, etc.)
"""
import asyncio
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from fastapi import HTTPException

from .step_service import initialize_step_tracking, register_step, log_step


# Git URL patterns for GitHub and GitLab (flexible patterns)
# Using [^/\s]+ to match any characters except / and whitespace for username/repo
GIT_URL_PATTERNS = [
    r'^https?://(www\.)?github\.com/[^/\s]+/[^/\s]+',
    r'^https?://(www\.)?gitlab\.com/[^/\s]+/[^/\s]+',
    r'^git@github\.com:[^/\s]+/[^/\s]+(\.git)?$',
    r'^git@gitlab\.com:[^/\s]+/[^/\s]+(\.git)?$',
]

# Maximum repository size in bytes (1GB default)
MAX_REPO_SIZE = 1024 * 1024 * 1024  # 1GB

# Clone timeout in seconds (5 minutes)
CLONE_TIMEOUT = 300


def is_git_url(url: str) -> bool:
    """Check if the given URL is a GitHub or GitLab repository URL"""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    result = any(re.match(pattern, url) for pattern in GIT_URL_PATTERNS)
    # Debug logging to help diagnose issues
    if not result and url:
        print(f"[Git URL Check] URL '{url}' did not match any Git pattern")
        for i, pattern in enumerate(GIT_URL_PATTERNS):
            match = re.match(pattern, url)
            if match:
                print(f"[Git URL Check] Pattern {i} matched: {pattern}")
    elif result:
        print(f"[Git URL Check] URL '{url}' matched Git pattern")
    return result


async def clone_repository(git_url: str, base_dir: Path, scan_id: str, current_scan: dict, results_dir: Path, branch: Optional[str] = None) -> Path:
    """
    Clone a Git repository to a temporary directory.
    Returns the path to the cloned repository.
    Raises HTTPException on failure.
    """
    # Create temporary directory for clones
    tmp_dir = base_dir / "tmp"
    tmp_dir.mkdir(exist_ok=True)
    
    # Create unique temporary directory for this clone
    temp_dir = tempfile.mkdtemp(prefix="simpleseccheck_git_", dir=str(tmp_dir))
    temp_path = Path(temp_dir)
    
    try:
        print(f"[Git Clone] Cloning repository: {git_url}")
        print(f"[Git Clone] Target directory: {temp_path}")
        
        # Log Git clone step to frontend (before cloning starts)
        if scan_id and current_scan and results_dir:
            # Register and log Git Clone step
            initialize_step_tracking(current_scan)
            step_num = register_step("Git Clone", current_scan)
            if step_num:
                log_step("Git Clone", f"⏳ Step {step_num}: Cloning Git repository...", current_scan, results_dir, scan_id)
                print(f"[Git Clone] Step logged: ⏳ Step {step_num}: Cloning Git repository...")
        
        # Normalize Git URL (remove .git suffix if present, handle SSH URLs)
        clone_url = git_url.strip()
        if clone_url.startswith("git@"):
            # SSH URL - keep as is
            pass
        elif clone_url.endswith(".git"):
            # HTTPS URL with .git - keep as is
            pass
        else:
            # HTTPS URL without .git - add .git for better compatibility
            if not clone_url.endswith("/"):
                clone_url = clone_url + ".git"
        
        # Clone repository with shallow clone (depth=1) for faster cloning
        def run_git_clone():
            clone_cmd = ["git", "clone", "--depth", "1", "--single-branch", clone_url, str(temp_path)]
            # Add branch if specified
            if branch and branch.strip():
                clone_cmd.insert(-1, "--branch")
                clone_cmd.insert(-1, branch.strip())
                print(f"[Git Clone] Cloning branch: {branch.strip()}")
            return subprocess.run(
                clone_cmd,
                capture_output=True,
                text=True,
                check=True
            )
        
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, run_git_clone),
            timeout=CLONE_TIMEOUT
        )
        
        print(f"[Git Clone] Successfully cloned repository to {temp_path}")
        
        # Log Git clone completion step
        if scan_id and current_scan and results_dir:
            step_num = current_scan.get("step_names", {}).get("Git Clone")
            if step_num:
                log_step("Git Clone", f"✓ Step {step_num}: Git repository cloned successfully", current_scan, results_dir, scan_id)
                print(f"[Git Clone] Step logged: ✓ Step {step_num}: Git repository cloned successfully")
        
        # Check repository size (approximate)
        repo_size = sum(f.stat().st_size for f in temp_path.rglob('*') if f.is_file())
        if repo_size > MAX_REPO_SIZE:
            shutil.rmtree(temp_path, ignore_errors=True)
            raise HTTPException(
                status_code=400,
                detail=f"Repository too large ({repo_size / (1024*1024):.1f}MB > {MAX_REPO_SIZE / (1024*1024):.1f}MB). Maximum size is {MAX_REPO_SIZE / (1024*1024):.1f}MB."
            )
        
        print(f"[Git Clone] Repository size: {repo_size / (1024*1024):.1f}MB")
        return temp_path
        
    except asyncio.TimeoutError:
        shutil.rmtree(temp_path, ignore_errors=True)
        raise HTTPException(
            status_code=408,
            detail=f"Repository clone timeout after {CLONE_TIMEOUT} seconds. The repository might be too large or the network connection is slow."
        )
    except subprocess.CalledProcessError as e:
        shutil.rmtree(temp_path, ignore_errors=True)
        error_msg = e.stderr.strip() if e.stderr else e.stdout.strip() if e.stdout else "Unknown error"
        
        # Provide user-friendly error messages
        if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
            if branch and ("branch" in error_msg.lower() or "ref" in error_msg.lower()):
                raise HTTPException(
                    status_code=404,
                    detail=f"Branch '{branch}' not found in repository: {git_url}. Please check the branch name and ensure it exists."
                )
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Repository not found: {git_url}. Please check the URL and ensure the repository exists and is accessible."
                )
        elif "permission denied" in error_msg.lower() or "authentication" in error_msg.lower():
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {git_url}. Private repositories require authentication. Please ensure you have access to this repository."
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to clone repository: {error_msg}"
            )
    except Exception as e:
        shutil.rmtree(temp_path, ignore_errors=True)
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error while cloning repository: {str(e)}"
        )


def cleanup_temp_repository(temp_path: Optional[Path]) -> None:
    """
    Clean up temporary repository directory.
    Safe to call multiple times - ignores errors if directory doesn't exist.
    """
    if not temp_path:
        return
    
    try:
        temp_path_obj = Path(temp_path) if isinstance(temp_path, str) else temp_path
        if temp_path_obj.exists() and temp_path_obj.is_dir():
            shutil.rmtree(temp_path_obj, ignore_errors=True)
            print(f"[Cleanup] Successfully deleted temporary repository")
    except Exception as e:
        print(f"[Cleanup Error] Failed to delete {temp_path}: {e}")
