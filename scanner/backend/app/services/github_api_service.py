"""
GitHub API Service
Handles GitHub API interactions for bulk repository scanning:
- Repository listing (user/org repos)
- Rate limit management
- Token validation
- Repository metadata fetching
"""
import os
import time
import asyncio
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta
from fastapi import HTTPException
import httpx


# GitHub API Rate Limits
# Without token: 60 requests/hour (1 per minute)
# With token: 5000 requests/hour (~83 per minute)
RATE_LIMIT_WITHOUT_TOKEN = 60  # per hour
RATE_LIMIT_WITH_TOKEN = 5000  # per hour
RATE_LIMIT_WINDOW = 3600  # 1 hour in seconds

# Rate limit tracking (in-memory, resets on restart)
_rate_limit_remaining: int = RATE_LIMIT_WITHOUT_TOKEN
_rate_limit_reset: Optional[datetime] = None
_rate_limit_used: int = 0
_last_request_time: Optional[datetime] = None


class GitHubRepository:
    """Repository information from GitHub API"""
    def __init__(self, data: dict):
        self.name = data.get("name", "")
        self.full_name = data.get("full_name", "")
        self.url = data.get("html_url", "")
        self.clone_url = data.get("clone_url", "")
        self.ssh_url = data.get("ssh_url", "")
        self.private = data.get("private", False)
        self.size = data.get("size", 0)  # Size in KB
        self.language = data.get("language", "")
        self.description = data.get("description", "")
        self.default_branch = data.get("default_branch", "main")
        self.updated_at = data.get("updated_at", "")
        self.stargazers_count = data.get("stargazers_count", 0)
        self.forks_count = data.get("forks_count", 0)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "name": self.name,
            "full_name": self.full_name,
            "url": self.url,
            "clone_url": self.clone_url,
            "ssh_url": self.ssh_url,
            "private": self.private,
            "size": self.size,
            "size_mb": round(self.size / 1024, 2),  # Convert KB to MB
            "language": self.language,
            "description": self.description,
            "default_branch": self.default_branch,
            "updated_at": self.updated_at,
            "stargazers_count": self.stargazers_count,
            "forks_count": self.forks_count,
        }


class RateLimitInfo:
    """Rate limit information"""
    def __init__(self, remaining: int, reset: datetime, used: int, limit: int):
        self.remaining = remaining
        self.reset = reset
        self.used = used
        self.limit = limit
        self.has_token = limit > 100  # Token limit is 5000, no-token is 60
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        reset_timestamp = int(self.reset.timestamp()) if self.reset else None
        return {
            "remaining": self.remaining,
            "used": self.used,
            "limit": self.limit,
            "reset_timestamp": reset_timestamp,
            "reset_time": self.reset.isoformat() if self.reset else None,
            "has_token": self.has_token,
            "estimated_requests_available": self.remaining,
        }


def get_github_token() -> Optional[str]:
    """Get GitHub token from environment variable"""
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    return token if token else None


def get_rate_limit_info() -> RateLimitInfo:
    """Get current rate limit information"""
    global _rate_limit_remaining, _rate_limit_reset, _rate_limit_used
    
    # Check if rate limit window has reset
    if _rate_limit_reset and datetime.now() >= _rate_limit_reset:
        # Reset window
        limit = RATE_LIMIT_WITH_TOKEN if get_github_token() else RATE_LIMIT_WITHOUT_TOKEN
        _rate_limit_remaining = limit
        _rate_limit_used = 0
        _rate_limit_reset = None
    
    # If no reset time set, use default limit
    if _rate_limit_reset is None:
        limit = RATE_LIMIT_WITH_TOKEN if get_github_token() else RATE_LIMIT_WITHOUT_TOKEN
        _rate_limit_remaining = limit
        _rate_limit_used = 0
    
    return RateLimitInfo(
        remaining=_rate_limit_remaining,
        reset=_rate_limit_reset or (datetime.now() + timedelta(seconds=RATE_LIMIT_WINDOW)),
        used=_rate_limit_used,
        limit=RATE_LIMIT_WITH_TOKEN if get_github_token() else RATE_LIMIT_WITHOUT_TOKEN
    )


async def check_rate_limit() -> Tuple[bool, RateLimitInfo]:
    """
    Check if we can make a request based on rate limits.
    Returns: (can_make_request, rate_limit_info)
    """
    rate_limit = get_rate_limit_info()
    
    # Check if we've exceeded the limit
    if rate_limit.remaining <= 0:
        return False, rate_limit
    
    return True, rate_limit


async def wait_for_rate_limit(rate_limit: RateLimitInfo) -> None:
    """Wait until rate limit resets"""
    if rate_limit.reset:
        wait_seconds = (rate_limit.reset - datetime.now()).total_seconds()
        if wait_seconds > 0:
            print(f"[GitHub API] Rate limit exceeded. Waiting {wait_seconds:.0f} seconds until reset...")
            await asyncio.sleep(min(wait_seconds, 3600))  # Max 1 hour wait


async def make_github_request(url: str, params: Optional[dict] = None) -> Tuple[dict, RateLimitInfo]:
    """
    Make a GitHub API request with rate limit management.
    Returns: (response_data, rate_limit_info)
    """
    
    # Check rate limit before making request
    can_request, rate_limit = await check_rate_limit()
    if not can_request:
        await wait_for_rate_limit(rate_limit)
        # Re-check after waiting
        can_request, rate_limit = await check_rate_limit()
        if not can_request:
            raise HTTPException(
                status_code=429,
                detail=f"GitHub API rate limit exceeded. Reset at {rate_limit.reset.isoformat() if rate_limit.reset else 'unknown'}"
            )
    
    # Prepare request
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "SimpleSecCheck/1.0"
    }
    
    token = get_github_token()
    if token:
        headers["Authorization"] = f"token {token}"
    
    # Make request
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            
            # Update rate limit from response headers
            global _rate_limit_remaining, _rate_limit_reset, _rate_limit_used, _last_request_time
            
            remaining = int(response.headers.get("X-RateLimit-Remaining", rate_limit.remaining))
            limit = int(response.headers.get("X-RateLimit-Limit", rate_limit.limit))
            reset_timestamp = int(response.headers.get("X-RateLimit-Reset", 0))
            
            _rate_limit_remaining = remaining
            _rate_limit_used = limit - remaining
            _rate_limit_reset = datetime.fromtimestamp(reset_timestamp) if reset_timestamp > 0 else None
            _last_request_time = datetime.now()
            
            # Handle rate limit exceeded
            if response.status_code == 403 and "rate limit" in response.text.lower():
                rate_limit = get_rate_limit_info()
                raise HTTPException(
                    status_code=429,
                    detail=f"GitHub API rate limit exceeded. Reset at {rate_limit.reset.isoformat() if rate_limit.reset else 'unknown'}"
                )
            
            # Handle other errors
            response.raise_for_status()
            
            data = response.json()
            
            # Update rate limit info after successful request
            rate_limit = get_rate_limit_info()
            
            return data, rate_limit
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail="GitHub user or organization not found")
            elif e.response.status_code == 403:
                raise HTTPException(status_code=403, detail="Access forbidden. Check token permissions or rate limits.")
            elif e.response.status_code == 401:
                raise HTTPException(status_code=401, detail="GitHub token is invalid or expired")
            else:
                raise HTTPException(status_code=e.response.status_code, detail=f"GitHub API error: {e.response.text}")
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="GitHub API request timeout")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch from GitHub API: {str(e)}")


async def list_user_repositories(username: str, include_private: bool = False, max_repos: int = 100) -> Tuple[List[GitHubRepository], RateLimitInfo]:
    """
    List all repositories for a GitHub user or organization.
    
    Args:
        username: GitHub username or organization name
        include_private: Include private repositories (requires token with repo scope)
        max_repos: Maximum number of repositories to fetch (default 100)
    
    Returns:
        Tuple of (list of repositories, rate limit info)
    """
    repos = []
    page = 1
    per_page = 100  # GitHub API max
    
    token = get_github_token()
    if include_private and not token:
        raise HTTPException(
            status_code=400,
            detail="Private repositories require a GitHub token. Set GITHUB_TOKEN environment variable."
        )
    
    while len(repos) < max_repos:
        # Calculate how many to fetch this page
        remaining = max_repos - len(repos)
        current_per_page = min(per_page, remaining)
        
        url = f"https://api.github.com/users/{username}/repos"
        params = {
            "page": page,
            "per_page": current_per_page,
            "sort": "updated",
            "direction": "desc"
        }
        
        # If we have a token and want private repos, we need to use a different endpoint
        if token and include_private:
            url = f"https://api.github.com/user/repos"  # This lists repos for authenticated user
            params = {
                "page": page,
                "per_page": current_per_page,
                "sort": "updated",
                "direction": "desc",
                "affiliation": "owner,collaborator,organization_member"  # Include all affiliations
            }
        
        try:
            data, rate_limit = await make_github_request(url, params)
            
            # Handle empty response
            if not data or (isinstance(data, list) and len(data) == 0):
                break
            
            # Handle single repo (shouldn't happen, but be safe)
            if isinstance(data, dict):
                data = [data]
            
            # Filter by username if using user/repos endpoint
            if token and include_private and url.endswith("/user/repos"):
                data = [repo for repo in data if repo.get("owner", {}).get("login", "").lower() == username.lower()]
            
            # Convert to GitHubRepository objects
            for repo_data in data:
                repos.append(GitHubRepository(repo_data))
            
            # If we got fewer repos than requested, we've reached the end
            if len(data) < current_per_page:
                break
            
            page += 1
            
            # Small delay to be respectful to API
            await asyncio.sleep(0.5)
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to list repositories: {str(e)}")
    
    return repos[:max_repos], rate_limit


async def list_org_repositories(org_name: str, max_repos: int = 100) -> Tuple[List[GitHubRepository], RateLimitInfo]:
    """
    List all repositories for a GitHub organization.
    
    Args:
        org_name: GitHub organization name
        max_repos: Maximum number of repositories to fetch (default 100)
    
    Returns:
        Tuple of (list of repositories, rate limit info)
    """
    repos = []
    page = 1
    per_page = 100
    
    while len(repos) < max_repos:
        remaining = max_repos - len(repos)
        current_per_page = min(per_page, remaining)
        
        url = f"https://api.github.com/orgs/{org_name}/repos"
        params = {
            "page": page,
            "per_page": current_per_page,
            "sort": "updated",
            "direction": "desc"
        }
        
        try:
            data, rate_limit = await make_github_request(url, params)
            
            if not data or len(data) == 0:
                break
            
            for repo_data in data:
                repos.append(GitHubRepository(repo_data))
            
            if len(data) < current_per_page:
                break
            
            page += 1
            await asyncio.sleep(0.5)
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to list organization repositories: {str(e)}")
    
    return repos[:max_repos], rate_limit


async def validate_github_token(token: str) -> Tuple[bool, dict]:
    """
    Validate a GitHub token by making an authenticated request.
    
    Returns:
        Tuple of (is_valid, user_info)
    """
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "SimpleSecCheck/1.0",
        "Authorization": f"token {token}"
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get("https://api.github.com/user", headers=headers)
            response.raise_for_status()
            user_data = response.json()
            return True, user_data
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return False, {"error": "Invalid or expired token"}
            else:
                return False, {"error": f"GitHub API error: {e.response.status_code}"}
        except Exception as e:
            return False, {"error": str(e)}
