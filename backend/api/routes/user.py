"""
User API Routes

Handles user-specific operations like API keys, GitHub repos, and profile management.
"""
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import secrets
import hashlib

from api.deps.actor_context import get_authenticated_user, ActorContext
from infrastructure.container import (
    get_scan_target_service,
    get_user_service,
    get_api_key_service,
    get_github_repo_service,
    get_repo_scan_history_repository,
    get_scan_repository,
)
from application.services.scan_target_service import ScanTargetService
from application.services.user_service import UserService
from application.services.api_key_service import ApiKeyService
from application.services.github_repo_service import GitHubRepoService
from domain.entities.github_repo import GitHubRepo
from domain.repositories.repo_scan_history_repository import RepoScanHistoryRepository
from domain.repositories.scan_repository import ScanRepository
from domain.services.audit_log_service import AuditLogService
from uuid import UUID


def get_scan_target_service_dependency() -> ScanTargetService:
    """FastAPI dependency for ScanTargetService (DDD)."""
    return get_scan_target_service()


def get_user_service_dependency() -> UserService:
    """FastAPI dependency for UserService (DDD)."""
    return get_user_service()


def get_api_key_service_dependency() -> ApiKeyService:
    """FastAPI dependency for ApiKeyService (DDD)."""
    return get_api_key_service()


def get_github_repo_service_dependency() -> GitHubRepoService:
    """FastAPI dependency for GitHubRepoService (DDD)."""
    return get_github_repo_service()


def get_repo_scan_history_repository_dependency() -> RepoScanHistoryRepository:
    """FastAPI dependency for RepoScanHistoryRepository (DDD)."""
    return get_repo_scan_history_repository()


def get_scan_repository_dependency() -> ScanRepository:
    """FastAPI dependency for ScanRepository (DDD)."""
    return get_scan_repository()


def _github_repo_to_response(
    repo: GitHubRepo,
    last_scan: Optional[Dict[str, Any]] = None,
    score: Optional[int] = None,
    vulnerabilities: Optional[Dict[str, int]] = None,
    last_webhook_triggered_at: Optional[str] = None,
) -> "GitHubRepoResponse":
    """Build GitHubRepoResponse from domain entity and optional last_scan."""
    return GitHubRepoResponse(
        id=repo.id,
        repo_url=repo.repo_url,
        repo_owner=repo.repo_owner,
        repo_name=repo.repo_name,
        branch=repo.branch,
        auto_scan_enabled=repo.auto_scan_enabled,
        scan_on_push=repo.scan_on_push,
        scan_frequency=repo.scan_frequency,
        scanners=repo.scanners,
        created_at=repo.created_at.isoformat(),
        updated_at=repo.updated_at.isoformat(),
        last_scan=last_scan,
        score=score,
        vulnerabilities=vulnerabilities,
        last_webhook_triggered_at=last_webhook_triggered_at,
    )


router = APIRouter(
    prefix="/api/user",
    tags=["user"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        500: {"description": "Internal Server Error"},
    },
)


# ============================================================================
# API Key Management
# ============================================================================

class APIKeyCreateRequest(BaseModel):
    """Request for creating an API key."""
    name: str = Field(..., min_length=1, max_length=255, description="API key name")
    expires_in_days: Optional[int] = Field(None, ge=1, description="Expiration in days (null = never expires)")


class APIKeyResponse(BaseModel):
    """Response for API key information."""
    id: str
    name: str
    key_prefix: str  # First 8 chars for display
    created_at: str
    last_used_at: Optional[str] = None
    expires_at: Optional[str] = None
    is_active: bool


class APIKeyCreateResponse(BaseModel):
    """Response when creating an API key (includes full key)."""
    id: str
    name: str
    api_key: str  # Full key (only shown once)
    created_at: str
    expires_at: Optional[str] = None


def generate_api_key(user_id: str) -> str:
    """Generate a new API key."""
    random_part = secrets.token_urlsafe(32)
    return f"ssc_{user_id[:8]}_{random_part}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    actor_context: ActorContext = Depends(get_authenticated_user),
    api_key_service: ApiKeyService = Depends(get_api_key_service_dependency),
) -> List[APIKeyResponse]:
    """
    List all API keys for the current user.
    
    Requires authentication.
    """
    try:
        if not actor_context.user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        keys = await api_key_service.list_by_user(actor_context.user_id, active_only=True)
        return [
            APIKeyResponse(
                id=key.id,
                name=key.name,
                key_prefix=key.key_hash[:8],
                created_at=key.created_at.isoformat(),
                last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
                expires_at=key.expires_at.isoformat() if key.expires_at else None,
                is_active=key.is_active,
            )
            for key in keys
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list API keys: {str(e)}"
        )


@router.post("/api-keys", response_model=APIKeyCreateResponse)
async def create_api_key(
    request: Request,
    key_data: APIKeyCreateRequest,
    actor_context: ActorContext = Depends(get_authenticated_user),
    api_key_service: ApiKeyService = Depends(get_api_key_service_dependency),
) -> APIKeyCreateResponse:
    """
    Create a new API key for the current user.
    
    Requires authentication.
    The full API key is only returned once in the response.
    """
    try:
        if not actor_context.user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        plain_key = generate_api_key(actor_context.user_id)
        key_hash = hash_api_key(plain_key)
        created = await api_key_service.create(
            actor_context.user_id,
            key_data.name,
            key_hash,
            expires_in_days=key_data.expires_in_days,
        )
        await AuditLogService.log_event(
            user_id=actor_context.user_id,
            user_email=actor_context.email,
            action_type="API_KEY_CREATED",
            target=key_data.name,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent")
        )
        return APIKeyCreateResponse(
            id=created.id,
            name=created.name,
            api_key=plain_key,
            created_at=created.created_at.isoformat(),
            expires_at=created.expires_at.isoformat() if created.expires_at else None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create API key: {str(e)}"
        )


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    request: Request,
    key_id: str,
    actor_context: ActorContext = Depends(get_authenticated_user),
    api_key_service: ApiKeyService = Depends(get_api_key_service_dependency),
) -> Dict[str, str]:
    """
    Revoke (delete) an API key.
    
    Requires authentication.
    Users can only revoke their own API keys.
    """
    try:
        if not actor_context.user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        key = await api_key_service.get_by_id(key_id, actor_context.user_id)
        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        revoked = await api_key_service.revoke(key_id, actor_context.user_id)
        if not revoked:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        await AuditLogService.log_event(
            user_id=actor_context.user_id,
            user_email=actor_context.email,
            action_type="API_KEY_REVOKED",
            target=key.name,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent")
        )
        return {"message": "API key revoked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke API key: {str(e)}"
        )


@router.get("/api-keys/{key_id}/usage")
async def get_api_key_usage(
    key_id: str,
    actor_context: ActorContext = Depends(get_authenticated_user),
    api_key_service: ApiKeyService = Depends(get_api_key_service_dependency),
) -> Dict[str, Any]:
    """
    Get usage statistics for an API key.
    
    Requires authentication.
    Users can only view usage for their own API keys.
    """
    try:
        if not actor_context.user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        key = await api_key_service.get_by_id(key_id, actor_context.user_id)
        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        # TODO: Implement actual usage tracking
        # For now, return basic info
        return {
            "key_id": key.id,
            "name": key.name,
            "created_at": key.created_at.isoformat(),
            "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
            "total_requests": 0,  # TODO: Track requests
            "requests_today": 0,  # TODO: Track requests
            "requests_this_week": 0,  # TODO: Track requests
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get API key usage: {str(e)}"
        )


# ============================================================================
# Profile Management
# ============================================================================

class ProfileResponse(BaseModel):
    """Response for user profile."""
    user_id: str
    email: str
    username: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: str
    last_login: Optional[str] = None


class PasswordChangeRequest(BaseModel):
    """Request for changing password."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    actor_context: ActorContext = Depends(get_authenticated_user),
    user_service: UserService = Depends(get_user_service_dependency),
) -> ProfileResponse:
    """
    Get current user's profile information.
    
    Requires authentication.
    """
    try:
        if not actor_context.user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        user = await user_service.get_by_id(actor_context.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return ProfileResponse(
            user_id=user.id,
            email=user.email,
            username=user.username,
            role=user.role.value,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get profile: {str(e)}"
        )


@router.post("/profile/password", response_model=Dict[str, str])
async def change_password(
    request: Request,
    password_data: PasswordChangeRequest,
    actor_context: ActorContext = Depends(get_authenticated_user),
    user_service: UserService = Depends(get_user_service_dependency),
) -> Dict[str, str]:
    """
    Change user's password.
    
    Requires authentication.
    """
    try:
        if not actor_context.user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        from api.services.password_service import PasswordService
        password_service = PasswordService()
        user = await user_service.get_by_id(actor_context.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        if not password_service.verify_password(password_data.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        await user_service.update_password(
            actor_context.user_id,
            password_service.hash_password(password_data.new_password),
        )
        await AuditLogService.log_event(
            user_id=actor_context.user_id,
            user_email=actor_context.email,
            action_type="PASSWORD_CHANGED",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent")
        )
        return {"message": "Password changed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to change password: {str(e)}"
        )


# ============================================================================
# GitHub Repository Management
# ============================================================================

class GitHubRepoAddRequest(BaseModel):
    """Request for adding a GitHub repository."""
    repo_url: str = Field(..., description="GitHub repository URL")
    branch: str = Field(default="main", description="Branch to scan")
    auto_scan_enabled: bool = Field(default=True, description="Enable auto-scanning")
    scan_on_push: bool = Field(default=True, description="Scan on push events")
    scan_frequency: str = Field(default="on_push", pattern="^(on_push|daily|weekly|manual)$")
    github_token: Optional[str] = Field(None, description="GitHub Personal Access Token (optional)")


class GitHubRepoUpdateRequest(BaseModel):
    """Request for updating a GitHub repository."""
    branch: Optional[str] = None
    auto_scan_enabled: Optional[bool] = None
    scan_on_push: Optional[bool] = None
    scan_frequency: Optional[str] = Field(None, pattern="^(on_push|daily|weekly|manual)$")
    scanners: Optional[List[str]] = None  # Scanner selection for this repo


class GitHubRepoResponse(BaseModel):
    """Response for GitHub repository information."""
    id: str
    repo_url: str
    repo_owner: Optional[str] = None  # GitHub username/organization (e.g. "fr4iser90")
    repo_name: str  # Repository name only (e.g. "my-repo"), NOT "owner/repo"
    branch: str
    auto_scan_enabled: bool
    scan_on_push: bool
    scan_frequency: str
    scanners: Optional[List[str]] = None  # Scanner selection for this repo
    created_at: str
    updated_at: str
    last_scan: Optional[Dict[str, Any]] = None
    score: Optional[int] = None
    vulnerabilities: Optional[Dict[str, int]] = None
    last_webhook_triggered_at: Optional[str] = None  # ISO datetime of last scan triggered by webhook (push/PR)


def extract_repo_owner(repo_url: str) -> Optional[str]:
    """
    Extract repository owner (username/organization) from URL.
    
    Examples:
    - https://github.com/fr4iser90/my-repo -> "fr4iser90"
    - https://github.com/fr4iser90/my-repo.git -> "fr4iser90"
    - git@github.com:fr4iser90/my-repo.git -> "fr4iser90"
    """
    if not repo_url:
        return None
    
    # Remove .git suffix and trailing slashes
    repo_url = repo_url.replace(".git", "").rstrip("/")
    
    # Handle GitHub URLs: https://github.com/owner/repo
    if "github.com" in repo_url:
        if "github.com/" in repo_url:
            parts = repo_url.split("github.com/")[-1]
            if "/" in parts:
                return parts.split("/")[0]
        elif "github.com:" in repo_url:
            parts = repo_url.split("github.com:")[-1]
            if "/" in parts:
                return parts.split("/")[0]
    
    # Handle GitLab URLs: https://gitlab.com/owner/repo
    if "gitlab.com" in repo_url:
        if "gitlab.com/" in repo_url:
            parts = repo_url.split("gitlab.com/")[-1]
            if "/" in parts:
                return parts.split("/")[0]
    
    # Fallback: try to extract from path
    parts = repo_url.split("/")
    if len(parts) >= 2:
        return parts[-2]
    
    return None


def extract_repo_name(repo_url: str) -> str:
    """
    Extract repository name ONLY (not owner/repo) from URL.
    
    Examples:
    - https://github.com/fr4iser90/my-repo -> "my-repo"
    - https://github.com/fr4iser90/my-repo.git -> "my-repo"
    - git@github.com:fr4iser90/my-repo.git -> "my-repo"
    """
    if not repo_url:
        return ""
    
    # Remove .git suffix and trailing slashes
    repo_url = repo_url.replace(".git", "").rstrip("/")
    
    # Handle GitHub URLs: https://github.com/owner/repo
    if "github.com" in repo_url:
        if "github.com/" in repo_url:
            parts = repo_url.split("github.com/")[-1]
            if "/" in parts:
                return parts.split("/")[-1]
        elif "github.com:" in repo_url:
            parts = repo_url.split("github.com:")[-1]
            if "/" in parts:
                return parts.split("/")[-1]
    
    # Handle GitLab URLs: https://gitlab.com/owner/repo
    if "gitlab.com" in repo_url:
        if "gitlab.com/" in repo_url:
            parts = repo_url.split("gitlab.com/")[-1]
            if "/" in parts:
                return parts.split("/")[-1]
    
    # Fallback: try to extract from path
    parts = repo_url.split("/")
    if len(parts) >= 1:
        return parts[-1]
    
    return repo_url


@router.get("/github/repos", response_model=List[GitHubRepoResponse])
async def list_github_repos(
    actor_context: ActorContext = Depends(get_authenticated_user),
    github_repo_service: GitHubRepoService = Depends(get_github_repo_service_dependency),
    repo_scan_history_repository: RepoScanHistoryRepository = Depends(get_repo_scan_history_repository_dependency),
) -> List[GitHubRepoResponse]:
    """
    List all GitHub repositories for the current user.
    
    Requires authentication.
    """
    try:
        if not actor_context.user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        repos = await github_repo_service.list_by_user(actor_context.user_id)
        repo_ids = [r.id for r in repos]
        last_scans = await repo_scan_history_repository.get_latest_by_repo_ids(repo_ids)
        last_webhook = await repo_scan_history_repository.get_last_webhook_triggered_at(repo_ids)
        return [
            _github_repo_to_response(
                repo,
                last_scan=last_scans[repo.id].to_last_scan_dict() if repo.id in last_scans else None,
                score=last_scans[repo.id].score if repo.id in last_scans else None,
                vulnerabilities=last_scans[repo.id].vulnerabilities if repo.id in last_scans else None,
                last_webhook_triggered_at=last_webhook[repo.id].isoformat() if repo.id in last_webhook else None,
            )
            for repo in repos
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list GitHub repos: {str(e)}"
        )


@router.post("/github/repos", response_model=GitHubRepoResponse)
async def add_github_repo(
    request: Request,
    repo_data: GitHubRepoAddRequest,
    actor_context: ActorContext = Depends(get_authenticated_user),
    github_repo_service: GitHubRepoService = Depends(get_github_repo_service_dependency),
) -> GitHubRepoResponse:
    """
    Add a new GitHub repository.
    
    Requires authentication.
    """
    try:
        if not actor_context.user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        if "github.com" not in repo_data.repo_url and "github.com" not in repo_data.repo_url.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid GitHub repository URL"
            )
        repo_name = extract_repo_name(repo_data.repo_url)
        repo_owner = extract_repo_owner(repo_data.repo_url)
        existing = await github_repo_service.get_by_user_and_url(
            actor_context.user_id, repo_data.repo_url
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Repository already added"
            )
        new_repo = await github_repo_service.create(
            actor_context.user_id,
            repo_data.repo_url,
            repo_name,
            repo_owner=repo_owner,
            branch=repo_data.branch,
            auto_scan_enabled=repo_data.auto_scan_enabled,
            scan_on_push=repo_data.scan_on_push,
            scan_frequency=repo_data.scan_frequency,
            github_token=repo_data.github_token,
        )
        await AuditLogService.log_event(
            user_id=actor_context.user_id,
            user_email=actor_context.email,
            action_type="REPO_ADDED",
            target=repo_data.repo_url,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent")
        )
        return _github_repo_to_response(new_repo)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add GitHub repo: {str(e)}"
        )


@router.get("/github/repos/{repo_id}", response_model=GitHubRepoResponse)
async def get_github_repo(
    repo_id: str,
    actor_context: ActorContext = Depends(get_authenticated_user),
    github_repo_service: GitHubRepoService = Depends(get_github_repo_service_dependency),
    repo_scan_history_repository: RepoScanHistoryRepository = Depends(get_repo_scan_history_repository_dependency),
) -> GitHubRepoResponse:
    """
    Get details for a specific GitHub repository.
    
    Requires authentication.
    Users can only access their own repositories.
    """
    try:
        if not actor_context.user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        repo = await github_repo_service.get_by_id(repo_id, actor_context.user_id)
        if not repo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository not found"
            )
        last_scans = await repo_scan_history_repository.get_latest_by_repo_ids([repo.id])
        entry = last_scans.get(repo.id)
        last_webhook = await repo_scan_history_repository.get_last_webhook_triggered_at([repo.id])
        return _github_repo_to_response(
            repo,
            last_scan=entry.to_last_scan_dict() if entry else None,
            score=entry.score if entry else None,
            vulnerabilities=entry.vulnerabilities if entry else None,
            last_webhook_triggered_at=last_webhook[repo.id].isoformat() if repo.id in last_webhook else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.put("/github/repos/{repo_id}", response_model=GitHubRepoResponse)
async def update_github_repo(
    request: Request,
    repo_id: str,
    repo_data: GitHubRepoUpdateRequest,
    actor_context: ActorContext = Depends(get_authenticated_user),
    github_repo_service: GitHubRepoService = Depends(get_github_repo_service_dependency),
    repo_scan_history_repository: RepoScanHistoryRepository = Depends(get_repo_scan_history_repository_dependency),
) -> GitHubRepoResponse:
    """
    Update a GitHub repository's settings.
    
    Requires authentication.
    Users can only update their own repositories.
    """
    try:
        if not actor_context.user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        try:
            updated = await github_repo_service.update(
                repo_id,
                actor_context.user_id,
                branch=repo_data.branch,
                auto_scan_enabled=repo_data.auto_scan_enabled,
                scan_on_push=repo_data.scan_on_push,
                scan_frequency=repo_data.scan_frequency,
                scanners=repo_data.scanners,
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository not found"
            )
        await AuditLogService.log_event(
            user_id=actor_context.user_id,
            user_email=actor_context.email,
            action_type="REPO_UPDATED",
            target=updated.repo_url,
            details={"changes": repo_data.model_dump(exclude_unset=True)},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent")
        )
        last_scans = await repo_scan_history_repository.get_latest_by_repo_ids([updated.id])
        entry = last_scans.get(updated.id)
        last_webhook = await repo_scan_history_repository.get_last_webhook_triggered_at([updated.id])
        return _github_repo_to_response(
            updated,
            last_scan=entry.to_last_scan_dict() if entry else None,
            score=entry.score if entry else None,
            vulnerabilities=entry.vulnerabilities if entry else None,
            last_webhook_triggered_at=last_webhook[updated.id].isoformat() if updated.id in last_webhook else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update GitHub repo: {str(e)}"
        )


@router.delete("/github/repos/{repo_id}")
async def remove_github_repo(
    request: Request,
    repo_id: str,
    actor_context: ActorContext = Depends(get_authenticated_user),
    github_repo_service: GitHubRepoService = Depends(get_github_repo_service_dependency),
) -> Dict[str, str]:
    """
    Remove a GitHub repository.
    
    Requires authentication.
    Users can only remove their own repositories.
    """
    try:
        if not actor_context.user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        repo = await github_repo_service.get_by_id(repo_id, actor_context.user_id)
        if not repo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository not found"
            )
        repo_url = repo.repo_url
        await github_repo_service.delete(repo_id, actor_context.user_id)
        await AuditLogService.log_event(
            user_id=actor_context.user_id,
            user_email=actor_context.email,
            action_type="REPO_REMOVED",
            target=repo_url,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent")
        )
        return {"message": "Repository removed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove GitHub repo: {str(e)}"
        )


@router.post("/github/repos/{repo_id}/scan")
async def trigger_repo_scan(
    request: Request,
    repo_id: str,
    actor_context: ActorContext = Depends(get_authenticated_user),
    github_repo_service: GitHubRepoService = Depends(get_github_repo_service_dependency),
) -> Dict[str, Any]:
    """
    Trigger a manual scan for a GitHub repository.
    
    Requires authentication.
    Users can only trigger scans for their own repositories.
    """
    try:
        if not actor_context.user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        repo = await github_repo_service.get_by_id(repo_id, actor_context.user_id)
        if not repo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository not found"
            )
        from domain.services.repo_scan_helper import create_repo_scan
        scan_id = await create_repo_scan(
            repo_url=repo.repo_url,
            repo_name=repo.repo_name,
            branch=repo.branch,
            user_id=actor_context.user_id,
            scanners=repo.scanners if repo.scanners else None,
            metadata={"trigger": "manual", "repo_id": repo.id}
        )
        if scan_id:
            await AuditLogService.log_event(
                user_id=actor_context.user_id,
                user_email=actor_context.email,
                action_type="REPO_SCAN_TRIGGERED",
                target=repo.repo_url,
                details={"scan_id": scan_id, "branch": repo.branch},
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent")
            )
            return {
                "message": "Scan triggered successfully",
                "repo_id": repo.id,
                "scan_id": scan_id,
                "status": "queued"
            }
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create scan"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger scan: {str(e)}"
        )


@router.get("/github/repos/{repo_id}/scan-status")
async def get_repo_scan_status(
    repo_id: str,
    actor_context: ActorContext = Depends(get_authenticated_user),
    github_repo_service: GitHubRepoService = Depends(get_github_repo_service_dependency),
    scan_repository: ScanRepository = Depends(get_scan_repository_dependency),
) -> Dict[str, Any]:
    """
    Get current scan status for a GitHub repository.
    
    Checks if there's an active scan (pending/running) for this repo.
    Returns scan status and queue position if applicable.
    
    Requires authentication.
    Users can only view status for their own repositories.
    """
    try:
        if not actor_context.user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        repo = await github_repo_service.get_by_id(repo_id, actor_context.user_id)
        if not repo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository not found"
            )
        active_scan = await scan_repository.find_active_scan_by_user_and_target(
            actor_context.user_id, repo.repo_url
        )
        if not active_scan:
            return {
                "has_active_scan": False,
                "status": None,
                "scan_id": None,
                "queue_position": None
            }
        queue_position = None
        if active_scan.status.value.lower() == "pending":
            queue_position = await scan_repository.get_queue_position(
                active_scan.id, actor_context.user_id
            )
        return {
            "has_active_scan": True,
            "status": active_scan.status.value.lower(),
            "scan_id": active_scan.id,
            "queue_position": queue_position,
            "created_at": active_scan.created_at.isoformat() if active_scan.created_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scan status: {str(e)}"
        )


@router.get("/github/repos/{repo_id}/history")
async def get_repo_scan_history(
    repo_id: str,
    limit: int = 50,
    offset: int = 0,
    actor_context: ActorContext = Depends(get_authenticated_user),
    github_repo_service: GitHubRepoService = Depends(get_github_repo_service_dependency),
    repo_scan_history_repository: RepoScanHistoryRepository = Depends(get_repo_scan_history_repository_dependency),
) -> Dict[str, Any]:
    """
    Get scan history for a GitHub repository.
    
    Requires authentication.
    Users can only view history for their own repositories.
    """
    try:
        if not actor_context.user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        repo = await github_repo_service.get_by_id(repo_id, actor_context.user_id)
        if not repo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository not found"
            )
        entries, total = await repo_scan_history_repository.get_history_page(repo_id, limit, offset)
        return {
            "entries": [
                {
                    "id": h.id,
                    "scan_id": h.scan_id,
                    "branch": h.branch,
                    "commit_hash": h.commit_hash,
                    "score": h.score,
                    "vulnerabilities": h.vulnerabilities,
                    "created_at": h.created_at.isoformat()
                }
                for h in entries
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scan history: {str(e)}"
        )


# ============================================================================
# Scan Targets (My Targets) – generic saved targets
# ============================================================================

class ScanTargetCreateRequest(BaseModel):
    """Request for creating a scan target."""
    type: str = Field(..., description="Target type: git_repo, container_registry, local_mount, ...")
    source: str = Field(..., min_length=1, max_length=1000, description="Primary identifier: URL, image name, path")
    display_name: Optional[str] = Field(None, max_length=255)
    auto_scan: Optional[Dict[str, Any]] = Field(default_factory=dict)
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    scanners: Optional[List[str]] = Field(default=None, description="Scanner names for this target; empty/None = use defaults")


class ScanTargetUpdateRequest(BaseModel):
    """Request for updating a scan target."""
    display_name: Optional[str] = None
    auto_scan: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None
    scanners: Optional[List[str]] = None


class LastScanSummary(BaseModel):
    """Summary of the latest scan for a target (for dashboard overview)."""
    scan_id: str
    status: str
    completed_at: Optional[str] = None
    total_vulnerabilities: int = 0
    critical_vulnerabilities: int = 0
    high_vulnerabilities: int = 0
    medium_vulnerabilities: int = 0
    low_vulnerabilities: int = 0


class ScanTargetResponse(BaseModel):
    """Response for a scan target."""
    id: str
    user_id: str
    type: str
    source: str
    display_name: Optional[str] = None
    auto_scan: Dict[str, Any]
    config: Dict[str, Any]
    created_at: str
    updated_at: str
    scanners: List[str] = []
    last_scan: Optional[LastScanSummary] = None
    next_scan_at: Optional[str] = None  # ISO datetime when next interval scan is due (null if not auto-interval)


def _last_scan_to_summary(scan_row: Any) -> Optional[LastScanSummary]:
    """Build LastScanSummary from a Scan model row or Scan entity or None."""
    if not scan_row:
        return None
    status = getattr(scan_row.status, "value", scan_row.status) or str(scan_row.status)
    return LastScanSummary(
        scan_id=str(scan_row.id),
        status=status,
        completed_at=scan_row.completed_at.isoformat() if getattr(scan_row, "completed_at", None) else None,
        total_vulnerabilities=getattr(scan_row, "total_vulnerabilities", 0) or 0,
        critical_vulnerabilities=getattr(scan_row, "critical_vulnerabilities", 0) or 0,
        high_vulnerabilities=getattr(scan_row, "high_vulnerabilities", 0) or 0,
        medium_vulnerabilities=getattr(scan_row, "medium_vulnerabilities", 0) or 0,
        low_vulnerabilities=getattr(scan_row, "low_vulnerabilities", 0) or 0,
    )


def _next_scan_at(auto_scan: Dict[str, Any], last_summary: Optional[LastScanSummary]) -> Optional[str]:
    """Compute next scan time for interval-based auto_scan. Returns ISO datetime or None."""
    if not auto_scan or not auto_scan.get("enabled") or auto_scan.get("mode") != "interval":
        return None
    interval_seconds = (auto_scan or {}).get("interval_seconds")
    if not interval_seconds or int(interval_seconds) <= 0:
        return None
    if not last_summary or not last_summary.completed_at:
        return None
    from datetime import datetime, timedelta
    try:
        completed = datetime.fromisoformat(last_summary.completed_at.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    next_at = completed + timedelta(seconds=int(interval_seconds))
    return next_at.isoformat()


@router.get("/targets", response_model=List[ScanTargetResponse])
async def list_scan_targets(
    target_type: Optional[str] = None,
    actor_context: ActorContext = Depends(get_authenticated_user),
    scan_target_service: ScanTargetService = Depends(get_scan_target_service_dependency),
    scan_repository: ScanRepository = Depends(get_scan_repository_dependency),
) -> List[ScanTargetResponse]:
    """
    List all scan targets for the current user (My Targets).
    Includes scanners (default for target type) and last_scan summary for dashboard overview.
    Optional filter by target_type.
    """
    if not actor_context.user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    targets = await scan_target_service.list_by_user(actor_context.user_id, target_type=target_type)
    if not targets:
        return []

    from domain.services.target_scan_helper import get_default_scanner_names_for_target_type

    sources = [t.source for t in targets]
    latest_by_url = await scan_repository.get_latest_scans_by_target_urls(actor_context.user_id, sources)

    scanner_cache: Dict[str, List[str]] = {}
    for t in targets:
        if t.type not in scanner_cache:
            scanner_cache[t.type] = await get_default_scanner_names_for_target_type(t.type)

    def _scanners_for_target(t) -> List[str]:
        custom = t.config.get("scanners") if isinstance(t.config, dict) else None
        return custom if isinstance(custom, list) else scanner_cache.get(t.type, [])

    return [
        ScanTargetResponse(
            id=str(t.id),
            user_id=str(t.user_id),
            type=t.type,
            source=t.source,
            display_name=t.display_name or None,
            auto_scan=t.auto_scan.to_dict(),
            config=t.config,
            created_at=t.created_at.isoformat(),
            updated_at=t.updated_at.isoformat(),
            scanners=_scanners_for_target(t),
            last_scan=_last_scan_to_summary(latest_by_url.get(t.source)),
            next_scan_at=_next_scan_at(t.auto_scan.to_dict(), _last_scan_to_summary(latest_by_url.get(t.source))),
        )
        for t in targets
    ]


@router.post("/targets", response_model=ScanTargetResponse)
async def create_scan_target(
    request: Request,
    body: ScanTargetCreateRequest,
    actor_context: ActorContext = Depends(get_authenticated_user),
    scan_target_service: ScanTargetService = Depends(get_scan_target_service_dependency),
) -> ScanTargetResponse:
    """
    Create a new scan target. Validates source and config per target_type.
    Dangerous types (e.g. local_mount) require admin.
    """
    if not actor_context.user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    config = dict(body.config or {})
    if body.scanners is not None:
        config["scanners"] = body.scanners
    try:
        created = await scan_target_service.create_target(
            actor_context.user_id,
            body.type,
            body.source,
            config,
            display_name=body.display_name,
            auto_scan=body.auto_scan,
            actor_role=actor_context.role or "user",
        )
    except ValueError as e:
        detail = str(e)
        if "already added" in detail or "Invalid target type" in detail:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
    except Exception as e:
        detail = str(e)
        if "permission" in detail.lower() or "denied" in detail.lower() or "disabled" in detail.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    await AuditLogService.log_event(
        user_id=actor_context.user_id,
        user_email=actor_context.email,
        action_type="TARGET_ADDED",
        target=created.source,
        details={"target_type": created.type, "target_id": created.id},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    # Enqueue one initial scan so the new target gets a first run without waiting for interval
    try:
        await scan_target_service.trigger_scan(
            created.id,
            actor_context.user_id,
            metadata_extra={"trigger": "initial_scan"},
        )
    except Exception as e:
        import logging
        logging.getLogger("api.user").warning("Initial scan enqueue failed for target %s: %s", created.id, e)
    from domain.services.target_scan_helper import get_default_scanner_names_for_target_type
    _custom = created.config.get("scanners") if isinstance(created.config, dict) else None
    _scanners = _custom if isinstance(_custom, list) else await get_default_scanner_names_for_target_type(created.type)
    return ScanTargetResponse(
        id=created.id,
        user_id=created.user_id,
        type=created.type,
        source=created.source,
        display_name=created.display_name,
        auto_scan=created.auto_scan.to_dict(),
        config=created.config,
        created_at=created.created_at.isoformat(),
        updated_at=created.updated_at.isoformat(),
        scanners=_scanners,
        last_scan=None,
        next_scan_at=None,
    )


@router.get("/targets/{target_id}", response_model=ScanTargetResponse)
async def get_scan_target(
    target_id: str,
    actor_context: ActorContext = Depends(get_authenticated_user),
    scan_target_service: ScanTargetService = Depends(get_scan_target_service_dependency),
    scan_repository: ScanRepository = Depends(get_scan_repository_dependency),
) -> ScanTargetResponse:
    """Get a single scan target by id."""
    if not actor_context.user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    target = await scan_target_service.get_by_id(target_id, actor_context.user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")
    from domain.services.target_scan_helper import get_default_scanner_names_for_target_type
    _custom = target.config.get("scanners") if isinstance(target.config, dict) else None
    _scanners = _custom if isinstance(_custom, list) else await get_default_scanner_names_for_target_type(target.type)
    latest_by_url = await scan_repository.get_latest_scans_by_target_urls(actor_context.user_id, [target.source])
    _last = _last_scan_to_summary(latest_by_url.get(target.source))
    return ScanTargetResponse(
        id=target.id,
        user_id=target.user_id,
        type=target.type,
        source=target.source,
        display_name=target.display_name,
        auto_scan=target.auto_scan.to_dict(),
        config=target.config,
        created_at=target.created_at.isoformat(),
        updated_at=target.updated_at.isoformat(),
        scanners=_scanners,
        last_scan=_last,
        next_scan_at=_next_scan_at(target.auto_scan.to_dict(), _last),
    )


@router.put("/targets/{target_id}", response_model=ScanTargetResponse)
async def update_scan_target(
    request: Request,
    target_id: str,
    body: ScanTargetUpdateRequest,
    actor_context: ActorContext = Depends(get_authenticated_user),
    scan_repository: ScanRepository = Depends(get_scan_repository_dependency),
) -> ScanTargetResponse:
    """Update a scan target. Config is validated per target_type."""
    if not actor_context.user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    from domain.services.target_handlers import get_target_handler
    from domain.entities.scan_target import ScanTarget
    from domain.value_objects.auto_scan_config import AutoScanConfig

    repo = _target_repo()
    target = await repo.get_by_id(target_id, actor_context.user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")

    if body.config is not None or body.scanners is not None:
        handler = get_target_handler(target.type)
        config_to_validate = dict(body.config if body.config is not None else target.config)
        if body.scanners is not None:
            config_to_validate["scanners"] = body.scanners
        if handler:
            target.config = handler.validate_config(config_to_validate)
    if body.auto_scan is not None:
        target.auto_scan = AutoScanConfig.from_dict(body.auto_scan)
    if body.display_name is not None:
        target.display_name = (body.display_name or "").strip() or None

    updated = await repo.update(target)
    await AuditLogService.log_event(
        user_id=actor_context.user_id,
        user_email=actor_context.email,
        action_type="TARGET_UPDATED",
        target=updated.source,
        details={"target_id": updated.id},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    from domain.services.target_scan_helper import get_default_scanner_names_for_target_type
    _custom = updated.config.get("scanners") if isinstance(updated.config, dict) else None
    _scanners = _custom if isinstance(_custom, list) else await get_default_scanner_names_for_target_type(updated.type)
    latest_by_url = await scan_repository.get_latest_scans_by_target_urls(actor_context.user_id, [updated.source])
    _last = _last_scan_to_summary(latest_by_url.get(updated.source))
    return ScanTargetResponse(
        id=updated.id,
        user_id=updated.user_id,
        type=updated.type,
        source=updated.source,
        display_name=updated.display_name,
        auto_scan=updated.auto_scan.to_dict(),
        config=updated.config,
        created_at=updated.created_at.isoformat(),
        updated_at=updated.updated_at.isoformat(),
        scanners=_scanners,
        last_scan=_last,
        next_scan_at=_next_scan_at(updated.auto_scan.to_dict(), _last),
    )


@router.post("/targets/{target_id}/scan")
async def trigger_scan_target(
    request: Request,
    target_id: str,
    actor_context: ActorContext = Depends(get_authenticated_user),
    scan_target_service: ScanTargetService = Depends(get_scan_target_service_dependency),
) -> Dict[str, Any]:
    """Trigger a scan for a saved target. Creates scan and enqueues it. Returns scan_id."""
    if not actor_context.user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    scan_id = await scan_target_service.trigger_scan(
        target_id,
        actor_context.user_id,
        metadata_extra={"trigger": "user_scan_now"},
        enforcement_mode="full",
    )
    if not scan_id:
        target = await scan_target_service.get_by_id(target_id, actor_context.user_id)
        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create scan for target",
        )
    await AuditLogService.log_event(
        user_id=actor_context.user_id,
        user_email=actor_context.email,
        action_type="TARGET_SCAN_TRIGGERED",
        target=target_id,
        details={"scan_id": scan_id},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    return {"scan_id": scan_id }


@router.delete("/targets/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scan_target(
    request: Request,
    target_id: str,
    actor_context: ActorContext = Depends(get_authenticated_user),
    scan_target_service: ScanTargetService = Depends(get_scan_target_service_dependency),
) -> None:
    """Delete a scan target."""
    if not actor_context.user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    deleted = await scan_target_service.delete(target_id, actor_context.user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")
    await AuditLogService.log_event(
        user_id=actor_context.user_id,
        user_email=actor_context.email,
        action_type="TARGET_REMOVED",
        target=target_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
