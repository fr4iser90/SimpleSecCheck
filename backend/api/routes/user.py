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
from infrastructure.database.adapter import db_adapter
from infrastructure.database.models import APIKey, User
from domain.services.audit_log_service import AuditLogService
from sqlalchemy import select
from uuid import UUID

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
        
        async with db_adapter.async_session() as session:
            user_uuid = UUID(actor_context.user_id)
            result = await session.execute(
                select(APIKey)
                .where(APIKey.user_id == user_uuid, APIKey.is_active == True)
                .order_by(APIKey.created_at.desc())
            )
            api_keys = result.scalars().all()
            
            return [
                APIKeyResponse(
                    id=str(key.id),
                    name=key.name,
                    key_prefix=key.key_hash[:8],  # Show first 8 chars of hash as prefix
                    created_at=key.created_at.isoformat(),
                    last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
                    expires_at=key.expires_at.isoformat() if key.expires_at else None,
                    is_active=key.is_active
                )
                for key in api_keys
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
        
        async with db_adapter.async_session() as session:
            user_uuid = UUID(actor_context.user_id)
            
            # Generate API key
            api_key = generate_api_key(actor_context.user_id)
            key_hash = hash_api_key(api_key)
            
            # Calculate expiration
            expires_at = None
            if key_data.expires_in_days:
                expires_at = datetime.utcnow() + timedelta(days=key_data.expires_in_days)
            
            # Create API key record
            new_key = APIKey(
                user_id=user_uuid,
                key_hash=key_hash,
                name=key_data.name,
                expires_at=expires_at,
                is_active=True
            )
            
            session.add(new_key)
            await session.commit()
            await session.refresh(new_key)
            
            # Log audit event
            await AuditLogService.log_event(
                user_id=actor_context.user_id,
                user_email=actor_context.email,
                action_type="API_KEY_CREATED",
                target=key_data.name,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent")
            )
            
            return APIKeyCreateResponse(
                id=str(new_key.id),
                name=new_key.name,
                api_key=api_key,  # Full key (only shown once)
                created_at=new_key.created_at.isoformat(),
                expires_at=new_key.expires_at.isoformat() if new_key.expires_at else None
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
        
        async with db_adapter.async_session() as session:
            user_uuid = UUID(actor_context.user_id)
            key_uuid = UUID(key_id)
            
            result = await session.execute(
                select(APIKey).where(
                    APIKey.id == key_uuid,
                    APIKey.user_id == user_uuid
                )
            )
            api_key = result.scalar_one_or_none()
            
            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="API key not found"
                )
            
            key_name = api_key.name
            
            # Soft delete (set is_active to False)
            api_key.is_active = False
            await session.commit()
            
            # Log audit event
            await AuditLogService.log_event(
                user_id=actor_context.user_id,
                user_email=actor_context.email,
                action_type="API_KEY_REVOKED",
                target=key_name,
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
        
        async with db_adapter.async_session() as session:
            user_uuid = UUID(actor_context.user_id)
            key_uuid = UUID(key_id)
            
            result = await session.execute(
                select(APIKey).where(
                    APIKey.id == key_uuid,
                    APIKey.user_id == user_uuid
                )
            )
            api_key = result.scalar_one_or_none()
            
            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="API key not found"
                )
            
            # TODO: Implement actual usage tracking
            # For now, return basic info
            return {
                "key_id": str(api_key.id),
                "name": api_key.name,
                "created_at": api_key.created_at.isoformat(),
                "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None,
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
        
        async with db_adapter.async_session() as session:
            user_uuid = UUID(actor_context.user_id)
            result = await session.execute(
                select(User).where(User.id == user_uuid)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            return ProfileResponse(
                user_id=str(user.id),
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
        
        async with db_adapter.async_session() as session:
            user_uuid = UUID(actor_context.user_id)
            result = await session.execute(
                select(User).where(User.id == user_uuid)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Verify current password
            if not password_service.verify_password(password_data.current_password, user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current password is incorrect"
                )
            
            # Update password
            user.password_hash = password_service.hash_password(password_data.new_password)
            user.updated_at = datetime.utcnow()
            await session.commit()
            
            # Log audit event
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
        
        from infrastructure.database.models import UserGitHubRepo, RepoScanHistory, Scan
        from sqlalchemy import desc
        
        async with db_adapter.async_session() as session:
            user_uuid = UUID(actor_context.user_id)
            result = await session.execute(
                select(UserGitHubRepo)
                .where(UserGitHubRepo.user_id == user_uuid)
                .order_by(UserGitHubRepo.created_at.desc())
            )
            repos = result.scalars().all()
            
            repo_responses = []
            for repo in repos:
                # Get last scan
                history_result = await session.execute(
                    select(RepoScanHistory)
                    .where(RepoScanHistory.repo_id == repo.id)
                    .order_by(desc(RepoScanHistory.created_at))
                    .limit(1)
                )
                last_history = history_result.scalar_one_or_none()
                
                last_scan = None
                if last_history:
                    last_scan = {
                        "scan_id": str(last_history.scan_id) if last_history.scan_id else None,
                        "score": last_history.score,
                        "vulnerabilities": last_history.vulnerabilities,
                        "created_at": last_history.created_at.isoformat()
                    }
                
                repo_responses.append(GitHubRepoResponse(
                    id=str(repo.id),
                    repo_url=repo.repo_url,
                    repo_owner=repo.repo_owner,
                    repo_name=repo.repo_name,
                    branch=repo.branch,
                    auto_scan_enabled=repo.auto_scan_enabled,
                    scan_on_push=repo.scan_on_push,
                    scan_frequency=repo.scan_frequency,
                    scanners=repo.scanners if repo.scanners else None,
                    created_at=repo.created_at.isoformat(),
                    updated_at=repo.updated_at.isoformat(),
                    last_scan=last_scan,
                    score=last_history.score if last_history else None,
                    vulnerabilities=last_history.vulnerabilities if last_history else None
                ))
            
            return repo_responses
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
        
        from infrastructure.database.models import UserGitHubRepo
        
        # Validate GitHub URL
        if "github.com" not in repo_data.repo_url and "github.com" not in repo_data.repo_url.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid GitHub repository URL"
            )
        
        repo_name = extract_repo_name(repo_data.repo_url)
        
        async with db_adapter.async_session() as session:
            user_uuid = UUID(actor_context.user_id)
            
            # Check if repo already exists for this user
            existing_result = await session.execute(
                select(UserGitHubRepo).where(
                    UserGitHubRepo.user_id == user_uuid,
                    UserGitHubRepo.repo_url == repo_data.repo_url
                )
            )
            existing = existing_result.scalar_one_or_none()
            
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Repository already added"
                )
            
            # Create repository record
            new_repo = UserGitHubRepo(
                user_id=user_uuid,
                repo_url=repo_data.repo_url,
                repo_name=repo_name,
                branch=repo_data.branch,
                auto_scan_enabled=repo_data.auto_scan_enabled,
                scan_on_push=repo_data.scan_on_push,
                scan_frequency=repo_data.scan_frequency,
                github_token=repo_data.github_token  # TODO: Encrypt this
            )
            
            session.add(new_repo)
            await session.commit()
            await session.refresh(new_repo)
            
            # Log audit event
            await AuditLogService.log_event(
                user_id=actor_context.user_id,
                user_email=actor_context.email,
                action_type="REPO_ADDED",
                target=repo_data.repo_url,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent")
            )
            
            return GitHubRepoResponse(
                id=str(new_repo.id),
                repo_url=new_repo.repo_url,
                repo_owner=new_repo.repo_owner,
                repo_name=new_repo.repo_name,
                branch=new_repo.branch,
                auto_scan_enabled=new_repo.auto_scan_enabled,
                scan_on_push=new_repo.scan_on_push,
                scan_frequency=new_repo.scan_frequency,
                scanners=new_repo.scanners if new_repo.scanners else None,
                created_at=new_repo.created_at.isoformat(),
                updated_at=new_repo.updated_at.isoformat(),
                last_scan=None,
                score=None,
                vulnerabilities=None
            )
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
        
        from infrastructure.database.models import UserGitHubRepo, RepoScanHistory
        from sqlalchemy import desc
        
        async with db_adapter.async_session() as session:
            user_uuid = UUID(actor_context.user_id)
            repo_uuid = UUID(repo_id)
            
            result = await session.execute(
                select(UserGitHubRepo).where(
                    UserGitHubRepo.id == repo_uuid,
                    UserGitHubRepo.user_id == user_uuid
                )
            )
            repo = result.scalar_one_or_none()
            
            if not repo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Repository not found"
                )
            
            # Get last scan
            history_result = await session.execute(
                select(RepoScanHistory)
                .where(RepoScanHistory.repo_id == repo.id)
                .order_by(desc(RepoScanHistory.created_at))
                .limit(1)
            )
            last_history = history_result.scalar_one_or_none()
            
            last_scan = None
            if last_history:
                last_scan = {
                    "scan_id": str(last_history.scan_id) if last_history.scan_id else None,
                    "score": last_history.score,
                    "vulnerabilities": last_history.vulnerabilities,
                    "created_at": last_history.created_at.isoformat()
                }
            
            return GitHubRepoResponse(
                id=str(repo.id),
                repo_url=repo.repo_url,
                repo_owner=repo.repo_owner,
                repo_name=repo.repo_name,
                branch=repo.branch,
                auto_scan_enabled=repo.auto_scan_enabled,
                scan_on_push=repo.scan_on_push,
                scan_frequency=repo.scan_frequency,
                scanners=repo.scanners if repo.scanners else None,
                created_at=repo.created_at.isoformat(),
                updated_at=repo.updated_at.isoformat(),
                last_scan=last_scan,
                score=last_history.score if last_history else None,
                vulnerabilities=last_history.vulnerabilities if last_history else None
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get GitHub repo: {str(e)}"
        )


@router.put("/github/repos/{repo_id}", response_model=GitHubRepoResponse)
async def update_github_repo(
    request: Request,
    repo_id: str,
    repo_data: GitHubRepoUpdateRequest,
    actor_context: ActorContext = Depends(get_authenticated_user),
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
        
        from infrastructure.database.models import UserGitHubRepo, RepoScanHistory
        from sqlalchemy import desc
        
        async with db_adapter.async_session() as session:
            user_uuid = UUID(actor_context.user_id)
            repo_uuid = UUID(repo_id)
            
            result = await session.execute(
                select(UserGitHubRepo).where(
                    UserGitHubRepo.id == repo_uuid,
                    UserGitHubRepo.user_id == user_uuid
                )
            )
            repo = result.scalar_one_or_none()
            
            if not repo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Repository not found"
                )
            
            # Update fields
            if repo_data.branch is not None:
                repo.branch = repo_data.branch
            if repo_data.auto_scan_enabled is not None:
                repo.auto_scan_enabled = repo_data.auto_scan_enabled
            if repo_data.scan_on_push is not None:
                repo.scan_on_push = repo_data.scan_on_push
            if repo_data.scan_frequency is not None:
                repo.scan_frequency = repo_data.scan_frequency
            if repo_data.scanners is not None:
                repo.scanners = repo_data.scanners
            
            repo.updated_at = datetime.utcnow()
            await session.commit()
            await session.refresh(repo)
            
            # Log audit event
            await AuditLogService.log_event(
                user_id=actor_context.user_id,
                user_email=actor_context.email,
                action_type="REPO_UPDATED",
                target=repo.repo_url,
                details={"changes": repo_data.dict(exclude_unset=True)},
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent")
            )
            
            # Get last scan
            history_result = await session.execute(
                select(RepoScanHistory)
                .where(RepoScanHistory.repo_id == repo.id)
                .order_by(desc(RepoScanHistory.created_at))
                .limit(1)
            )
            last_history = history_result.scalar_one_or_none()
            
            last_scan = None
            if last_history:
                last_scan = {
                    "scan_id": str(last_history.scan_id) if last_history.scan_id else None,
                    "score": last_history.score,
                    "vulnerabilities": last_history.vulnerabilities,
                    "created_at": last_history.created_at.isoformat()
                }
            
            return GitHubRepoResponse(
                id=str(repo.id),
                repo_url=repo.repo_url,
                repo_owner=repo.repo_owner,
                repo_name=repo.repo_name,
                branch=repo.branch,
                auto_scan_enabled=repo.auto_scan_enabled,
                scan_on_push=repo.scan_on_push,
                scan_frequency=repo.scan_frequency,
                scanners=repo.scanners if repo.scanners else None,
                created_at=repo.created_at.isoformat(),
                updated_at=repo.updated_at.isoformat(),
                last_scan=last_scan,
                score=last_history.score if last_history else None,
                vulnerabilities=last_history.vulnerabilities if last_history else None
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
        
        from infrastructure.database.models import UserGitHubRepo
        
        async with db_adapter.async_session() as session:
            user_uuid = UUID(actor_context.user_id)
            repo_uuid = UUID(repo_id)
            
            result = await session.execute(
                select(UserGitHubRepo).where(
                    UserGitHubRepo.id == repo_uuid,
                    UserGitHubRepo.user_id == user_uuid
                )
            )
            repo = result.scalar_one_or_none()
            
            if not repo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Repository not found"
                )
            
            repo_url = repo.repo_url
            
            await session.delete(repo)
            await session.commit()
            
            # Log audit event
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
        
        from infrastructure.database.models import UserGitHubRepo
        
        async with db_adapter.async_session() as session:
            user_uuid = UUID(actor_context.user_id)
            repo_uuid = UUID(repo_id)
            
            result = await session.execute(
                select(UserGitHubRepo).where(
                    UserGitHubRepo.id == repo_uuid,
                    UserGitHubRepo.user_id == user_uuid
                )
            )
            repo = result.scalar_one_or_none()
            
            if not repo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Repository not found"
                )
            
            # Create and queue scan
            from domain.services.repo_scan_helper import create_repo_scan
            
            scan_id = await create_repo_scan(
                repo_url=repo.repo_url,
                repo_name=repo.repo_name,
                branch=repo.branch,
                user_id=actor_context.user_id,
                scanners=repo.scanners if repo.scanners else None,  # Use repo-specific scanners if set
                metadata={
                    "trigger": "manual",
                    "repo_id": str(repo.id)
                }
            )
            
            if scan_id:
                # Log audit event
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
                    "repo_id": str(repo.id),
                    "scan_id": scan_id,
                    "status": "queued"
                }
            else:
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
        
        from infrastructure.database.models import UserGitHubRepo, Scan
        from sqlalchemy import and_, or_, func
        
        async with db_adapter.async_session() as session:
            user_uuid = UUID(actor_context.user_id)
            repo_uuid = UUID(repo_id)
            
            # Get repository
            repo_result = await session.execute(
                select(UserGitHubRepo).where(
                    UserGitHubRepo.id == repo_uuid,
                    UserGitHubRepo.user_id == user_uuid
                )
            )
            repo = repo_result.scalar_one_or_none()
            
            if not repo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Repository not found"
                )
            
            # Find active scans for this repo (pending or running)
            # Match by target_url containing the repo URL
            active_scan_result = await session.execute(
                select(Scan)
                .where(
                    and_(
                        Scan.user_id == user_uuid,
                        Scan.status.in_(["pending", "running"]),
                        Scan.target_url.contains(repo.repo_url)
                    )
                )
                .order_by(Scan.created_at.desc())
                .limit(1)
            )
            active_scan = active_scan_result.scalar_one_or_none()
            
            if not active_scan:
                return {
                    "has_active_scan": False,
                    "status": None,
                    "scan_id": None,
                    "queue_position": None
                }
            
            # Calculate queue position if pending
            queue_position = None
            if active_scan.status.lower() == "pending":
                position_query = select(func.count(Scan.id)).where(
                    and_(
                        Scan.status == "pending",
                        Scan.user_id == user_uuid,
                        or_(
                            Scan.priority > active_scan.priority,
                            and_(
                                Scan.priority == active_scan.priority,
                                Scan.created_at < active_scan.created_at
                            )
                        )
                    )
                )
                pos_result = await session.execute(position_query)
                queue_position = (pos_result.scalar() or 0) + 1
            
            return {
                "has_active_scan": True,
                "status": active_scan.status.lower(),
                "scan_id": str(active_scan.id),
                "queue_position": queue_position,
                "created_at": active_scan.created_at.isoformat()
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
        
        from infrastructure.database.models import UserGitHubRepo, RepoScanHistory
        from sqlalchemy import desc, func
        
        async with db_adapter.async_session() as session:
            user_uuid = UUID(actor_context.user_id)
            repo_uuid = UUID(repo_id)
            
            # Verify repo belongs to user
            repo_result = await session.execute(
                select(UserGitHubRepo).where(
                    UserGitHubRepo.id == repo_uuid,
                    UserGitHubRepo.user_id == user_uuid
                )
            )
            repo = repo_result.scalar_one_or_none()
            
            if not repo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Repository not found"
                )
            
            # Get total count
            count_result = await session.execute(
                select(func.count(RepoScanHistory.id)).where(
                    RepoScanHistory.repo_id == repo.id
                )
            )
            total = count_result.scalar() or 0
            
            # Get history entries
            history_result = await session.execute(
                select(RepoScanHistory)
                .where(RepoScanHistory.repo_id == repo.id)
                .order_by(desc(RepoScanHistory.created_at))
                .limit(limit)
                .offset(offset)
            )
            history = history_result.scalars().all()
            
            return {
                "entries": [
                    {
                        "id": str(h.id),
                        "scan_id": str(h.scan_id) if h.scan_id else None,
                        "branch": h.branch,
                        "commit_hash": h.commit_hash,
                        "score": h.score,
                        "vulnerabilities": h.vulnerabilities,
                        "created_at": h.created_at.isoformat()
                    }
                    for h in history
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
