"""
Health and Configuration Routes
"""
import os
from fastapi import APIRouter, HTTPException
from app.services import update_activity

router = APIRouter()

# Get environment from main (will be injected)
IS_PRODUCTION = None
ENVIRONMENT = None


def init_health_router(environment: str, is_production: bool):
    """Initialize router with environment variables"""
    global IS_PRODUCTION, ENVIRONMENT
    IS_PRODUCTION = is_production
    ENVIRONMENT = environment


@router.get("/api/health")
async def health():
    """Health check endpoint"""
    update_activity()
    return {"status": "ok", "service": "SimpleSecCheck WebUI"}


@router.get("/api/config")
async def get_config():
    """Get frontend configuration based on environment (backend-driven UI)"""
    zip_upload_enabled = os.getenv("ZIP_UPLOAD_ENABLED", "false").lower() == "true" if IS_PRODUCTION else True
    owasp_auto_update_enabled = os.getenv("OWASP_AUTO_UPDATE_ENABLED", "true" if IS_PRODUCTION else "false").lower() == "true"
    
    return {
        "environment": ENVIRONMENT,
        "is_production": IS_PRODUCTION,
        "features": {
            "scan_types": {
                "code": True,
                "website": not IS_PRODUCTION,
                "network": not IS_PRODUCTION,
            },
            "bulk_scan": not IS_PRODUCTION,
            "local_paths": not IS_PRODUCTION,
            "git_only": IS_PRODUCTION,
            "queue_enabled": IS_PRODUCTION,
            "session_management": IS_PRODUCTION,
            "metadata_collection": "always" if IS_PRODUCTION else "optional",
            "auto_shutdown": not IS_PRODUCTION,
            "zip_upload": zip_upload_enabled,
            "owasp_auto_update_enabled": owasp_auto_update_enabled,
        },
        "queue": {
            "max_length": int(os.getenv("MAX_QUEUE_LENGTH", "1000")),
            "public_view": IS_PRODUCTION,
        } if IS_PRODUCTION else None,
        "rate_limits": {
            "scans_per_session": int(os.getenv("RATE_LIMIT_PER_SESSION_SCANS", "10")),
            "requests_per_session": int(os.getenv("RATE_LIMIT_PER_SESSION_REQUESTS", "100")),
        } if IS_PRODUCTION else None,
    }


@router.get("/api/git/branches")
async def get_git_branches(url: str):
    """
    Get available branches from a Git repository.
    Uses git ls-remote to fetch branches without cloning.
    """
    update_activity()
    
    import subprocess
    import re
    
    # Validate URL
    if not url or not url.strip():
        raise HTTPException(status_code=400, detail="URL is required")
    
    git_url = url.strip()
    
    # Normalize Git URL (add .git if needed for HTTPS URLs)
    if not git_url.startswith("git@") and not git_url.endswith(".git") and not git_url.endswith("/"):
        git_url = git_url + ".git"
    
    try:
        # Use git ls-remote to fetch branches without cloning
        result = subprocess.run(
            ["git", "ls-remote", "--heads", git_url],
            capture_output=True,
            text=True,
            timeout=10,
            check=False
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            
            if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
                raise HTTPException(
                    status_code=404,
                    detail=f"Repository not found: {url}. Please check the URL and ensure the repository exists and is accessible."
                )
            elif "permission denied" in error_msg.lower() or "authentication" in error_msg.lower():
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {url}. Private repositories require authentication. You can still manually enter a branch name."
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to fetch branches: {error_msg}. You can still manually enter a branch name."
                )
        
        # Parse branches from output
        branches = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                match = re.search(r'refs/heads/(.+)', line)
                if match:
                    branch_name = match.group(1)
                    branches.append(branch_name)
        
        # Sort branches (put common ones first)
        common_branches = ['main', 'master', 'develop', 'dev', 'staging', 'production', 'prod']
        sorted_branches = []
        seen = set()
        
        for common in common_branches:
            if common in branches:
                sorted_branches.append(common)
                seen.add(common)
        
        for branch in sorted(branches):
            if branch not in seen:
                sorted_branches.append(branch)
        
        return {
            "branches": sorted_branches,
            "default": sorted_branches[0] if sorted_branches else None
        }
        
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=408,
            detail="Timeout while fetching branches. You can still manually enter a branch name."
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error while fetching branches: {str(e)}. You can still manually enter a branch name."
        )
