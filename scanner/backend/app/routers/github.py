"""
GitHub API Routes
"""
from fastapi import APIRouter, HTTPException
from app.services import update_activity
from app.services.github_api_service import (
    list_user_repositories,
    list_org_repositories,
    get_rate_limit_info,
    validate_github_token,
)

router = APIRouter()


def init_github_router():
    """Initialize router (no dependencies needed)"""
    pass


@router.get("/api/github/rate-limit")
async def get_github_rate_limit():
    """Get current GitHub API rate limit information"""
    update_activity()
    rate_limit = get_rate_limit_info()
    return rate_limit.to_dict()


@router.get("/api/github/repos")
async def get_github_repositories(
    username: str,
    include_private: bool = False,
    max_repos: int = 100
):
    """
    List repositories for a GitHub user or organization.
    
    Args:
        username: GitHub username or organization name
        include_private: Include private repositories (requires token)
        max_repos: Maximum number of repositories to fetch (default 100, max 100)
    """
    update_activity()
    
    # Validate max_repos
    max_repos = min(max(1, max_repos), 100)
    
    try:
        # Try as organization first, then as user
        try:
            repos, rate_limit = await list_org_repositories(username, max_repos)
        except HTTPException as e:
            if e.status_code == 404:
                # Not an org, try as user
                repos, rate_limit = await list_user_repositories(username, include_private, max_repos)
            else:
                raise
        
        return {
            "repositories": [repo.to_dict() for repo in repos],
            "rate_limit": rate_limit.to_dict(),
            "count": len(repos)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch repositories: {str(e)}")


@router.post("/api/github/validate-token")
async def validate_github_token_endpoint(token: str):
    """Validate a GitHub token"""
    update_activity()
    is_valid, user_info = await validate_github_token(token)
    return {
        "valid": is_valid,
        "user_info": user_info if is_valid else None
    }
