"""
Git API Routes

This module defines the FastAPI routes for Git operations.
"""
import subprocess  # nosec B404 - Used safely with hardcoded commands, timeouts, and shell=False
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from fastapi import status as fastapi_status
from pydantic import BaseModel
import httpx

from infrastructure.logging_config import get_logger
from domain.utils.git_repo_url import normalize_git_repo_url

logger = get_logger("api.git")

router = APIRouter(
    prefix="/api/git",
    tags=["git"],
    responses={
        400: {"description": "Bad Request"},
        500: {"description": "Internal Server Error"},
    },
)


class GitBranchesResponse(BaseModel):
    """Response model for Git branches endpoint."""
    branches: List[str]
    default: Optional[str] = None


def _is_valid_git_url(url: str) -> bool:
    """Check if URL is a valid Git repository URL."""
    if not url or not isinstance(url, str):
        return False
    
    url_lower = url.lower().strip()
    
    # Check for common Git URL patterns
    valid_patterns = [
        "https://github.com/",
        "https://gitlab.com/",
        "http://github.com/",
        "http://gitlab.com/",
        "git@github.com:",
        "git@gitlab.com:",
        ".git",
    ]
    
    return any(pattern in url_lower for pattern in valid_patterns)


def _get_branches_from_git_url(repo_url: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Get branches from a Git repository URL using git ls-remote.
    
    Args:
        repo_url: Git repository URL
        timeout: Timeout in seconds for git command
        
    Returns:
        Dict with 'branches' (list of branch names) and 'default' (default branch name)
    """
    branches = []
    default_branch = None
    
    try:
        # Use git ls-remote to get branches without cloning
        # Security: Hardcoded git command, URL is validated, timeout set
        result = subprocess.run(  # nosec B603, B607
            ["git", "ls-remote", "--heads", "--symref", repo_url],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        
        if result.returncode != 0:
            logger.warning(f"git ls-remote failed for {repo_url}: {result.stderr}")
            return {"branches": [], "default": None}
        
        # Parse output
        # Format: ref: refs/heads/main	HEAD
        #         abc123...	refs/heads/main
        #         def456...	refs/heads/develop
        for line in result.stdout.strip().split('\n'):
            if not line.strip():
                continue
            
            parts = line.split('\t')
            if len(parts) < 2:
                continue
            
            ref = parts[0].strip()
            branch_ref = parts[1].strip()
            
            # Check if this is the default branch (HEAD)
            if ref.startswith('ref:') and branch_ref == 'HEAD':
                # Extract default branch from next line or from ref
                # Format: ref: refs/heads/main	HEAD
                ref_parts = ref.split()
                if len(ref_parts) >= 2:
                    default_ref = ref_parts[1]
                    if default_ref.startswith('refs/heads/'):
                        default_branch = default_ref.replace('refs/heads/', '')
            
            # Extract branch name from refs/heads/branch_name
            if branch_ref.startswith('refs/heads/'):
                branch_name = branch_ref.replace('refs/heads/', '')
                if branch_name not in branches:
                    branches.append(branch_name)
        
        # If no default branch found, try common defaults
        if not default_branch and branches:
            for common_default in ['main', 'master', 'develop', 'dev']:
                if common_default in branches:
                    default_branch = common_default
                    break
            # If still no default, use first branch
            if not default_branch:
                default_branch = branches[0]
        
        logger.info(f"Found {len(branches)} branches for {repo_url}, default: {default_branch}")
        return {"branches": sorted(branches), "default": default_branch}
        
    except subprocess.TimeoutExpired:
        logger.error(f"git ls-remote timed out for {repo_url}")
        raise HTTPException(
            status_code=fastapi_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Git operation timed out"
        )
    except FileNotFoundError:
        logger.error("git command not found")
        raise HTTPException(
            status_code=fastapi_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Git is not available on the server"
        )
    except Exception as e:
        logger.error(f"Failed to get branches from {repo_url}: {e}", exc_info=True)
        raise HTTPException(
            status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch branches: {str(e)}"
        )


@router.get("/branches", response_model=GitBranchesResponse)
async def get_git_branches(
    url: str = Query(..., description="Git repository URL")
):
    """
    Get list of branches from a Git repository URL.
    
    Uses git ls-remote to fetch branches without cloning the repository.
    Supports GitHub, GitLab, and other Git hosting services.
    
    Args:
        url: Git repository URL (e.g., https://github.com/user/repo.git)
        
    Returns:
        GitBranchesResponse with list of branches and default branch
    """
    if not url or not url.strip():
        raise HTTPException(
            status_code=fastapi_status.HTTP_400_BAD_REQUEST,
            detail="URL parameter is required"
        )
    
    repo_url = url.strip()
    normalized = normalize_git_repo_url(repo_url)
    if normalized != repo_url:
        logger.info("Normalized Git URL for branch list: %s -> %s", repo_url, normalized)
    repo_url = normalized
    
    # Validate URL
    if not _is_valid_git_url(repo_url):
        logger.warning(f"Invalid Git URL provided: {repo_url}")
        raise HTTPException(
            status_code=fastapi_status.HTTP_400_BAD_REQUEST,
            detail="Invalid Git repository URL"
        )
    
    try:
        result = _get_branches_from_git_url(repo_url)
        return GitBranchesResponse(
            branches=result["branches"],
            default=result["default"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching branches: {e}", exc_info=True)
        raise HTTPException(
            status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch branches"
        )


class GitHubRepoInfo(BaseModel):
    """GitHub repository information."""
    full_name: str
    html_url: str
    description: Optional[str] = None
    default_branch: str = "main"
    stargazers_count: int = 0
    forks_count: int = 0
    private: bool = False


class GitHubReposResponse(BaseModel):
    """Response model for GitHub repos discovery endpoint."""
    repos: List[GitHubRepoInfo]


@router.get("/repos", response_model=GitHubReposResponse)
async def discover_github_repos(
    username: str = Query(..., description="GitHub username or organization name"),
    include_private: bool = Query(False, description="Include private repositories (requires GitHub token)"),
    github_token: Optional[str] = Query(None, description="GitHub Personal Access Token (optional, for private repos)"),
    max_repos: int = Query(100, ge=1, le=1000, description="Maximum number of repositories to return")
) -> GitHubReposResponse:
    """
    Discover all repositories for a GitHub user or organization.
    
    Uses GitHub API to fetch repositories without authentication (public repos only).
    For private repositories, a GitHub token is required.
    
    Args:
        username: GitHub username or organization name
        include_private: Whether to include private repositories
        github_token: GitHub Personal Access Token (optional)
        max_repos: Maximum number of repositories to return
        
    Returns:
        GitHubReposResponse with list of repositories
    """
    if not username or not username.strip():
        raise HTTPException(
            status_code=fastapi_status.HTTP_400_BAD_REQUEST,
            detail="Username parameter is required"
        )
    
    username = username.strip()
    
    try:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SimpleSecCheck"
        }
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        
        params = {
            "per_page": min(max_repos, 100),
            "sort": "updated",
            "direction": "desc"
        }
        repos = []
        page = 1
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Resolve user vs org: /users/{name} for users, /orgs/{name} for organizations
            user_resp = await client.get(f"https://api.github.com/users/{username}", headers=headers)
            if user_resp.status_code == 200:
                repos_url = f"https://api.github.com/users/{username}/repos"
            else:
                org_resp = await client.get(f"https://api.github.com/orgs/{username}", headers=headers)
                if org_resp.status_code == 200:
                    repos_url = f"https://api.github.com/orgs/{username}/repos"
                else:
                    raise HTTPException(
                        status_code=fastapi_status.HTTP_404_NOT_FOUND,
                        detail=f"User or organization '{username}' not found"
                    )
            
            while len(repos) < max_repos:
                params["page"] = page
                response = await client.get(repos_url, params=params, headers=headers)
                
                if response.status_code == 404:
                    raise HTTPException(
                        status_code=fastapi_status.HTTP_404_NOT_FOUND,
                        detail=f"User or organization '{username}' not found"
                    )
                elif response.status_code == 403:
                    raise HTTPException(
                        status_code=fastapi_status.HTTP_403_FORBIDDEN,
                        detail="GitHub API rate limit exceeded. Please try again later or provide a GitHub token."
                    )
                elif response.status_code != 200:
                    raise HTTPException(
                        status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"GitHub API error: {response.status_code}"
                    )
                
                data = response.json()
                if not data or len(data) == 0:
                    break
                
                for repo in data:
                    # Filter private repos if not including them
                    if not include_private and repo.get("private", False):
                        continue
                    
                    repos.append(GitHubRepoInfo(
                        full_name=repo.get("full_name", ""),
                        html_url=repo.get("html_url", ""),
                        description=repo.get("description"),
                        default_branch=repo.get("default_branch", "main"),
                        stargazers_count=repo.get("stargazers_count", 0),
                        forks_count=repo.get("forks_count", 0),
                        private=repo.get("private", False)
                    ))
                    
                    if len(repos) >= max_repos:
                        break
                
                # If we got less than 100 repos, we've reached the end
                if len(data) < 100:
                    break
                
                page += 1
        
        logger.info("Found %s repositories for '%s'", len(repos), username)
        return GitHubReposResponse(repos=repos)
        
    except httpx.TimeoutException:
        logger.error(f"Timeout while fetching GitHub repos for {username}")
        raise HTTPException(
            status_code=fastapi_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request to GitHub API timed out"
        )
    except httpx.RequestError as e:
        logger.error(f"Request error while fetching GitHub repos: {e}")
        raise HTTPException(
            status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect to GitHub API: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching GitHub repos: {e}", exc_info=True)
        raise HTTPException(
            status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch repositories: {str(e)}"
        )
