"""
Webhook API Routes

Handles webhooks from GitHub, GitLab, and other services for triggering scans.
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Header, status  # noqa: F401
from pydantic import BaseModel
import hmac
import hashlib
import logging

from api.deps.actor_context import get_actor_context, ActorContext
from domain.services.auto_scan_service import AutoScanService
from domain.services.audit_log_service import AuditLogService
from application.helpers.repo_scan_helper import create_repo_scan
from application.services.github_repo_service import GitHubRepoService
from infrastructure.container import get_github_repo_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/webhooks",
    tags=["webhooks"],
    responses={
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal Server Error"},
    },
)


# ============================================================================
# GitHub Webhook
# ============================================================================

def verify_github_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook signature."""
    if not secret:
        return False
    
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected_signature}", signature)


def get_github_repo_service_dependency() -> GitHubRepoService:
    return get_github_repo_service()


@router.post("/github")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_github_delivery: str = Header(..., alias="X-GitHub-Delivery"),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    github_repo_service: GitHubRepoService = Depends(get_github_repo_service_dependency),
) -> Dict[str, str]:
    """
    Handle GitHub webhook events.
    
    Supports:
    - push events: Trigger scan for repository
    - ping events: Webhook verification
    
    Authentication: GitHub webhook secret (configured per repo)
    """
    try:
        # Get raw body for signature verification
        body = await request.body()
        payload = await request.json()
        
        # Log webhook received
        logger.info(f"GitHub webhook received: {x_github_event} (delivery: {x_github_delivery})")
        
        # Handle ping event (webhook verification)
        if x_github_event == "ping":
            return {"message": "Webhook verified", "delivery": x_github_delivery}
        
        # Handle push event
        if x_github_event == "push":
            repo_url = payload.get("repository", {}).get("html_url")
            branch = payload.get("ref", "").replace("refs/heads/", "")
            commit_hash = payload.get("after")
            
            if not repo_url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Repository URL not found in payload"
                )
            
            repo = await github_repo_service.get_by_repo_url_with_auto_scan(repo_url)
            if not repo:
                logger.warning(f"Repository not found or auto-scan disabled: {repo_url}")
                return {"message": "Repository not found or auto-scan disabled"}
            
            if repo.webhook_secret and x_hub_signature_256:
                if not verify_github_signature(body, x_hub_signature_256, repo.webhook_secret):
                    logger.warning(f"Invalid webhook signature for repo: {repo_url}")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid webhook signature"
                    )
            
            await AuditLogService.log_event(
                user_id=repo.user_id,
                action_type="WEBHOOK_RECEIVED",
                target=repo_url,
                details={"event": x_github_event, "branch": branch, "commit": commit_hash},
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent")
            )
            
            if branch != repo.branch:
                logger.info(f"Webhook branch {branch} does not match repo branch {repo.branch}, skipping scan")
                return {
                    "message": "Branch mismatch, scan skipped",
                    "repo_id": repo.id,
                    "branch": branch,
                    "expected_branch": repo.branch
                }
            
            scan_id = await create_repo_scan(
                repo_url=repo_url,
                repo_name=repo.repo_name,
                branch=branch,
                user_id=repo.user_id,
                scanners=repo.scanners if repo.scanners else None,
                commit_hash=commit_hash,
                metadata={"webhook_event": x_github_event, "webhook_delivery": x_github_delivery}
            )
            
            if scan_id:
                logger.info(f"Webhook triggered scan {scan_id} for {repo_url} (branch: {branch})")
                return {
                    "message": "Scan triggered successfully",
                    "repo_id": repo.id,
                    "scan_id": scan_id,
                    "branch": branch,
                    "commit": commit_hash,
                    "status": "queued"
                }
            logger.error(f"Failed to create scan for {repo_url}")
            return {"message": "Failed to create scan", "repo_id": repo.id, "branch": branch}
        
        # Unknown event type
        logger.info(f"Unhandled GitHub event: {x_github_event}")
        return {"message": f"Event {x_github_event} received but not handled"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process GitHub webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process webhook: {str(e)}"
        )


# ============================================================================
# Generic Webhook
# ============================================================================

class GenericWebhookRequest(BaseModel):
    """Request for generic webhook."""
    event: str = "push"
    repo_url: str
    branch: str = "main"
    commit: Optional[str] = None
    user_id: Optional[str] = None


@router.post("/generic")
async def generic_webhook(
    request: Request,
    webhook_data: GenericWebhookRequest,
    actor_context: ActorContext = Depends(get_actor_context),
    github_repo_service: GitHubRepoService = Depends(get_github_repo_service_dependency),
) -> Dict[str, Any]:
    """
    Handle generic webhook events.
    
    Can be used by any Git service or CI/CD system.
    Requires API key authentication or user authentication.
    """
    try:
        # Determine user_id (from webhook data or actor context)
        user_id = webhook_data.user_id or actor_context.user_id
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required (API key or user session)"
            )
        
        repo = await github_repo_service.get_by_user_and_url(user_id, webhook_data.repo_url)
        if not repo or not repo.auto_scan_enabled:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository not found or auto-scan disabled"
            )
        
        await AuditLogService.log_event(
            user_id=user_id,
            action_type="WEBHOOK_RECEIVED",
            target=webhook_data.repo_url,
            details={
                "event": webhook_data.event,
                "branch": webhook_data.branch,
                "commit": webhook_data.commit
            },
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent")
        )
        
        if webhook_data.branch != repo.branch:
            logger.info(f"Webhook branch {webhook_data.branch} does not match repo branch {repo.branch}, skipping scan")
            return {
                "message": "Branch mismatch, scan skipped",
                "repo_id": repo.id,
                "branch": webhook_data.branch,
                "expected_branch": repo.branch
            }
        
        scan_id = await create_repo_scan(
            repo_url=webhook_data.repo_url,
            repo_name=repo.repo_name,
            branch=webhook_data.branch,
            user_id=user_id,
            scanners=repo.scanners if repo.scanners else None,
            commit_hash=webhook_data.commit,
            metadata={"webhook_event": webhook_data.event, "webhook_type": "generic"}
        )
        
        if scan_id:
            logger.info(f"Generic webhook triggered scan {scan_id} for {webhook_data.repo_url}")
            return {
                "message": "Scan triggered successfully",
                "repo_id": repo.id,
                "scan_id": scan_id,
                "branch": webhook_data.branch,
                "commit": webhook_data.commit,
                "status": "queued"
            }
        logger.error(f"Failed to create scan for {webhook_data.repo_url}")
        return {"message": "Failed to create scan", "repo_id": repo.id, "branch": webhook_data.branch}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process generic webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process webhook: {str(e)}"
        )


# ============================================================================
# Pre-Commit Hook
# ============================================================================

@router.post("/pre-commit")
async def pre_commit_hook(
    request: Request,
    actor_context: ActorContext = Depends(get_actor_context),
) -> Dict[str, Any]:
    """
    Handle pre-commit hook requests.
    
    Scans code before commit (via ZIP upload) and returns results.
    Can block commit if critical vulnerabilities found.
    """
    try:
        # Get form data (ZIP file)
        form = await request.form()
        zip_file = form.get("zip_file")
        repo_url = form.get("repo_url")
        branch = form.get("branch", "main")
        commit_message = form.get("commit_message", "")
        
        if not zip_file or not repo_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="zip_file and repo_url are required"
            )
        
        # TODO: Process ZIP file and trigger scan
        # For now, return placeholder
        
        return {
            "message": "Pre-commit scan triggered",
            "should_block": False,  # TODO: Determine based on scan results
            "scan_id": None  # TODO: Return actual scan ID
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process pre-commit hook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process pre-commit hook: {str(e)}"
        )
