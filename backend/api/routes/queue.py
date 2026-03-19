"""
Queue API Routes

This module defines the FastAPI routes for queue operations.
Queue data is read from PostgreSQL database (not Redis).
Redis is only used for job processing, PostgreSQL is the source of truth.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as fastapi_status

from api.deps.actor_context import get_actor_context, ActorContext
from infrastructure.container import get_scan_repository, get_user_service
from domain.repositories.scan_repository import ScanRepository
from domain.entities.user import UserRole
from application.services.user_service import UserService
from infrastructure.logging_config import get_logger
from domain.services.scanner_duration_service import ScannerDurationService
from domain.datetime_serialization import isoformat_utc

logger = get_logger("api.queue")

router = APIRouter(
    prefix="/api/queue",
    tags=["queue"],
    responses={
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        404: {"description": "Not Found"},
        500: {"description": "Internal Server Error"},
    },
)


def _extract_repository_name(target_url: str) -> str:
    """Extract repository name from target URL."""
    # Handle different URL formats
    if not target_url:
        return "Unknown"
    
    # Git URL formats: https://github.com/user/repo.git, git@github.com:user/repo.git
    if "github.com" in target_url or "gitlab.com" in target_url:
        parts = target_url.replace(".git", "").split("/")
        if len(parts) >= 2:
            return parts[-1]
    
    # Local paths
    if "/" in target_url:
        return target_url.split("/")[-1]
    
    return target_url


def _extract_branch_from_config(config: Dict[str, Any]) -> Optional[str]:
    """Extract branch from scan config."""
    if not config:
        return None
    return config.get("git_branch") or config.get("branch")


def _scan_status_str(scan: Any) -> str:
    """Normalize scan status to lowercase string (works with DB model or domain entity)."""
    s = getattr(scan, "status", None)
    raw = getattr(s, "value", s) if s is not None else None
    return str(raw or "pending").lower()


async def _scan_to_queue_item(scan: Any, position: Optional[int] = None, show_branch: bool = False) -> Dict[str, Any]:
    """
    Convert Scan model or entity to queue item format.
    """
    repository_name = _extract_repository_name(getattr(scan, "target_url", None) or "")
    config = getattr(scan, "config", None) or {}
    branch = _extract_branch_from_config(config) if show_branch else None
    
    status_map = {
        "pending": "pending",
        "running": "running",
        "completed": "completed",
        "failed": "failed",
        "cancelled": "failed",
    }
    queue_status = status_map.get(_scan_status_str(scan), _scan_status_str(scan))
    
    scanners = getattr(scan, "scanners", None) or []
    estimated_time_seconds = None
    if queue_status in ["pending", "running"] and scanners:
        estimated_time_seconds = await ScannerDurationService.get_estimated_time(scanners)
    
    duration_seconds = None
    if getattr(scan, "duration", None) is not None:
        duration_seconds = scan.duration
    else:
        started_at = getattr(scan, "started_at", None)
        completed_at = getattr(scan, "completed_at", None)
        if started_at and completed_at:
            duration_seconds = int((completed_at - started_at).total_seconds())
        elif started_at and queue_status == "running":
            from datetime import datetime
            duration_seconds = int((datetime.utcnow() - started_at).total_seconds())
    
    created_at = getattr(scan, "created_at", None)
    result = {
        "queue_id": str(scan.id),
        "repository_name": repository_name,
        "status": queue_status,
        "scanners": scanners,
        "position": position,
        "created_at": isoformat_utc(created_at),
        "scan_id": str(scan.id),
        "estimated_time_seconds": estimated_time_seconds,
        "duration_seconds": duration_seconds,
    }
    
    # Only include branch if show_branch is True (for authenticated users)
    if show_branch and branch:
        result["branch"] = branch
    
    return result


async def _scan_to_my_scan_item(scan: Any, position: Optional[int] = None) -> Dict[str, Any]:
    """Convert Scan model or entity to my-scans item format."""
    target_url = getattr(scan, "target_url", None) or ""
    config = getattr(scan, "config", None) or {}
    repository_name = _extract_repository_name(target_url)
    branch = _extract_branch_from_config(config)
    
    commit_hash = None
    metadata = getattr(scan, "scan_metadata", None) or {}
    if metadata:
        commit_hash = metadata.get("commit_hash") or metadata.get("commit")
    if not commit_hash and config:
        commit_hash = config.get("commit_hash") or config.get("commit")
    
    queue_status = {"pending": "pending", "running": "running", "completed": "completed", "failed": "failed", "cancelled": "failed"}.get(_scan_status_str(scan), _scan_status_str(scan))
    scanners = getattr(scan, "scanners", None) or []
    estimated_time_seconds = None
    if queue_status in ["pending", "running"] and scanners:
        estimated_time_seconds = await ScannerDurationService.get_estimated_time(scanners)
    
    duration_seconds = None
    if getattr(scan, "duration", None) is not None:
        duration_seconds = scan.duration
    else:
        started_at = getattr(scan, "started_at", None)
        completed_at = getattr(scan, "completed_at", None)
        if started_at and completed_at:
            duration_seconds = int((completed_at - started_at).total_seconds())
        elif started_at and queue_status == "running":
            from datetime import datetime
            duration_seconds = int((datetime.utcnow() - started_at).total_seconds())
    
    created_at = getattr(scan, "created_at", None)
    started_at = getattr(scan, "started_at", None)
    completed_at = getattr(scan, "completed_at", None)
    return {
        "queue_id": str(scan.id),
        "repository_url": target_url,
        "repository_name": repository_name,
        "branch": branch,
        "commit_hash": commit_hash,
        "status": queue_status,
        "scan_id": str(scan.id),
        "position": position,
        "created_at": isoformat_utc(created_at),
        "started_at": isoformat_utc(started_at),
        "completed_at": isoformat_utc(completed_at),
        "scanners": scanners,
        "estimated_time_seconds": estimated_time_seconds,
        "duration_seconds": duration_seconds,
    }


async def _is_admin_user(actor_context: ActorContext, user_service: Optional[UserService] = None) -> bool:
    """Check if the current user is an admin."""
    if not actor_context.is_authenticated or not actor_context.user_id:
        return False
    try:
        svc = user_service or get_user_service()
        user = await svc.get_by_id(actor_context.user_id)
        return user is not None and user.role == UserRole.ADMIN
    except Exception as e:
        logger.warning(f"Failed to check admin status: {e}")
    return False


def get_scan_repository_dependency() -> ScanRepository:
    return get_scan_repository()


@router.get(
    "/",
    summary="Get queue status",
    description="Get all scans in queue view format (anonymized). Shows all scans from database filtered by status (pending, running, completed, failed). Everyone sees all scans anonymized.",
)
async def get_queue(
    limit: int = Query(100, ge=1, le=1000, description="Limit results"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (pending, running, completed, failed)"),
    actor_context: ActorContext = Depends(get_actor_context),
    scan_repository: ScanRepository = Depends(get_scan_repository_dependency),
) -> Dict[str, Any]:
    """
    Get queue status with scans (Public Queue - anonymized).
    """
    try:
        scans = await scan_repository.get_queue_items(status_filter=status_filter, limit=limit, offset=0)
        statuses = [status_filter] if status_filter else ["pending", "running"]
        queue_length = await scan_repository.count_by_statuses(statuses)
        items = []
        for scan in scans:
            position = await scan_repository.get_position_in_queue(scan.id)
            items.append(await _scan_to_queue_item(scan, position, show_branch=False))
        return {
            "items": items,
            "queue_length": queue_length,
            "max_queue_length": 100,
        }
    except Exception as e:
        logger.error(f"Failed to get queue: {e}", exc_info=True)
        raise HTTPException(
            status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get queue: {str(e)}"
        )


@router.get(
    "/my-scans",
    summary="Get my scans",
    description="Get all scans for the current user/session from database.",
)
async def get_my_scans(
    limit: int = Query(100, ge=1, le=1000, description="Limit results"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    actor_context: ActorContext = Depends(get_actor_context),
    scan_repository: ScanRepository = Depends(get_scan_repository_dependency),
) -> Dict[str, Any]:
    """Get scans for the current user/session."""
    try:
        user_id = None
        guest_session_id = None
        if actor_context.is_authenticated and actor_context.user_id:
            try:
                from uuid import UUID
                UUID(actor_context.user_id)
                user_id = actor_context.user_id
            except (ValueError, TypeError):
                return {"scans": []}
        elif actor_context.session_id:
            guest_session_id = actor_context.session_id
        else:
            return {"scans": []}
        scans = await scan_repository.list_scans_for_actor(
            user_id=user_id,
            guest_session_id=guest_session_id,
            status_filter=status_filter,
            limit=limit,
        )
        items = []
        for scan in scans:
            position = await scan_repository.get_position_in_queue(scan.id)
            items.append(await _scan_to_my_scan_item(scan, position))
        return {"scans": items}
    except Exception as e:
        logger.error(f"Failed to get my scans: {e}", exc_info=True)
        raise HTTPException(
            status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get my scans: {str(e)}"
        )


@router.get(
    "/{scan_id}/status",
    summary="Get scan queue status",
    description="Get queue status for a specific scan.",
)
async def get_scan_queue_status(
    scan_id: str,
    actor_context: ActorContext = Depends(get_actor_context),
    scan_repository: ScanRepository = Depends(get_scan_repository_dependency),
) -> Dict[str, Any]:
    """Get queue status for a specific scan."""
    try:
        try:
            from uuid import UUID
            UUID(scan_id)
        except ValueError:
            raise HTTPException(
                status_code=fastapi_status.HTTP_400_BAD_REQUEST,
                detail="Invalid scan ID format"
            )
        scan = await scan_repository.get_by_id(scan_id)
        if not scan:
            raise HTTPException(
                status_code=fastapi_status.HTTP_404_NOT_FOUND,
                detail=f"Scan {scan_id} not found"
            )
        position = await scan_repository.get_position_in_queue(scan_id)
        queue_status = {"pending": "pending", "running": "running", "completed": "completed", "failed": "failed", "cancelled": "failed"}.get(_scan_status_str(scan), _scan_status_str(scan))
        scanners = getattr(scan, "scanners", None) or []
        estimated_time_seconds = None
        if queue_status in ["pending", "running"] and scanners:
            estimated_time_seconds = await ScannerDurationService.get_estimated_time(scanners)
        estimated_wait_seconds = None
        if queue_status in ["pending", "running"] and position and position > 1:
            scans_before = await scan_repository.get_scans_before_in_queue(scan_id)
            wait_total = 0.0
            for s in scans_before:
                sc = getattr(s, "scanners", None) or []
                if sc:
                    wait_total += await ScannerDurationService.get_estimated_time(sc)
            estimated_wait_seconds = int(wait_total) if wait_total else 0
        created_at = getattr(scan, "created_at", None)
        started_at = getattr(scan, "started_at", None)
        completed_at = getattr(scan, "completed_at", None)
        return {
            "queue_id": scan.id,
            "scan_id": scan.id,
            "repository_name": _extract_repository_name(getattr(scan, "target_url", None) or ""),
            "status": queue_status,
            "position": position,
            "created_at": isoformat_utc(created_at),
            "started_at": isoformat_utc(started_at),
            "completed_at": isoformat_utc(completed_at),
            "scanners": scanners,
            "estimated_time_seconds": estimated_time_seconds,
            "estimated_wait_seconds": estimated_wait_seconds,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get scan queue status: {e}", exc_info=True)
        raise HTTPException(
            status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scan queue status: {str(e)}"
        )


@router.delete(
    "/{scan_id}",
    summary="Delete scan from queue",
    description="Delete a scan from the queue. Users can only delete their own scans (if pending). Admins can delete any scan.",
)
async def delete_scan_from_queue(
    scan_id: str,
    actor_context: ActorContext = Depends(get_actor_context),
    scan_repository: ScanRepository = Depends(get_scan_repository_dependency),
) -> Dict[str, Any]:
    """Delete a scan from the queue; removes from Redis and sets status to cancelled."""
    try:
        try:
            from uuid import UUID
            UUID(scan_id)
        except ValueError:
            raise HTTPException(status_code=fastapi_status.HTTP_400_BAD_REQUEST, detail="Invalid scan ID format")
        scan = await scan_repository.get_by_id(scan_id)
        if not scan:
            raise HTTPException(status_code=fastapi_status.HTTP_404_NOT_FOUND, detail=f"Scan {scan_id} not found")
        is_admin = await _is_admin_user(actor_context)
        if not is_admin:
            if actor_context.is_authenticated and actor_context.user_id:
                if str(scan.user_id) != actor_context.user_id:
                    raise HTTPException(status_code=fastapi_status.HTTP_403_FORBIDDEN, detail="You can only delete your own scans")
            elif actor_context.session_id:
                meta = getattr(scan, "scan_metadata", None) or {}
                if meta.get("session_id") != actor_context.session_id:
                    raise HTTPException(status_code=fastapi_status.HTTP_403_FORBIDDEN, detail="You can only delete your own scans")
            else:
                raise HTTPException(status_code=fastapi_status.HTTP_403_FORBIDDEN, detail="Authentication required")
            if _scan_status_str(scan) != "pending":
                raise HTTPException(status_code=fastapi_status.HTTP_400_BAD_REQUEST, detail="You can only delete pending scans. Use cancel for running scans.")
        from infrastructure.services.queue_service import QueueService
        from application.services.scan_orchestration_service import ScanOrchestrationService
        from domain.entities.scan import ScanStatus
        queue_service = QueueService()
        removed_from_queue = await queue_service.remove_scan_from_queue(scan_id)
        if _scan_status_str(scan) == "running":
            await queue_service.signal_worker_cancel(scan_id)
            orch = ScanOrchestrationService()
            await orch.cancel_scan(scan_id)
        scan.status = ScanStatus.CANCELLED
        scan.updated_at = datetime.utcnow()
        scan.scan_metadata = dict(scan.scan_metadata or {})
        scan.scan_metadata["cancelled_at"] = isoformat_utc(datetime.utcnow())
        scan.scan_metadata["cancelled_by"] = actor_context.get_identifier()
        await scan_repository.update(scan)
        logger.info(f"Deleted scan {scan_id} from queue (removed from Redis: {removed_from_queue})")
        return {"success": True, "scan_id": scan_id, "removed_from_queue": removed_from_queue, "status": "cancelled", "message": "Scan deleted from queue successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete scan from queue: {e}", exc_info=True)
        raise HTTPException(status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete scan from queue: {str(e)}")


@router.post(
    "/{scan_id}/remove",
    summary="Remove scan from Redis queue only",
    description="Remove a scan from Redis queue without updating database. Admin only. Useful if scan is stuck in queue.",
)
async def remove_scan_from_redis_queue(
    scan_id: str,
    actor_context: ActorContext = Depends(get_actor_context),
) -> Dict[str, Any]:
    """
    Remove a scan from Redis queue only (does not update database).
    
    - **Admin only**
    - Useful if scan is stuck in Redis queue
    - Does not change scan status in database
    """
    try:
        is_admin = await _is_admin_user(actor_context)
        if not is_admin:
            raise HTTPException(
                status_code=fastapi_status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        
        from infrastructure.services.queue_service import QueueService
        
        queue_service = QueueService()
        removed = await queue_service.remove_scan_from_queue(scan_id)
        
        if not removed:
            raise HTTPException(
                status_code=fastapi_status.HTTP_404_NOT_FOUND,
                detail=f"Scan {scan_id} not found in Redis queue"
            )
        
        logger.info(f"Admin removed scan {scan_id} from Redis queue")
        
        return {
            "success": True,
            "scan_id": scan_id,
            "message": "Scan removed from Redis queue successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove scan from Redis queue: {e}", exc_info=True)
        raise HTTPException(
            status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove scan from Redis queue: {str(e)}"
        )


@router.patch(
    "/{scan_id}/position",
    summary="Change scan position in queue",
    description="Change the position of a scan in the queue by setting its priority. Admin only.",
)
async def change_scan_position(
    scan_id: str,
    position: int = Query(..., ge=1, description="New position in queue (1 = first)"),
    actor_context: ActorContext = Depends(get_actor_context),
    scan_repository: ScanRepository = Depends(get_scan_repository_dependency),
) -> Dict[str, Any]:
    """Change the position of a scan in the queue (admin only)."""
    try:
        is_admin = await _is_admin_user(actor_context)
        if not is_admin:
            raise HTTPException(status_code=fastapi_status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
        try:
            from uuid import UUID
            UUID(scan_id)
        except ValueError:
            raise HTTPException(status_code=fastapi_status.HTTP_400_BAD_REQUEST, detail="Invalid scan ID format")
        scan = await scan_repository.get_by_id(scan_id)
        if not scan:
            raise HTTPException(status_code=fastapi_status.HTTP_404_NOT_FOUND, detail=f"Scan {scan_id} not found")
        if _scan_status_str(scan) != "pending":
            raise HTTPException(status_code=fastapi_status.HTTP_400_BAD_REQUEST, detail=f"Cannot change position for scan with status '{_scan_status_str(scan)}'. Only pending scans can be reordered.")
        pending_scans = await scan_repository.get_queue_items(status_filter="pending", limit=1000, offset=0)
        if position > len(pending_scans):
            raise HTTPException(status_code=fastapi_status.HTTP_400_BAD_REQUEST, detail=f"Position {position} is out of range. There are only {len(pending_scans)} pending scans.")
        max_priority = 1000
        new_priority = max_priority - (position - 1)
        current_position = None
        for idx, s in enumerate(pending_scans):
            if s.id == scan_id:
                current_position = idx + 1
                break
        if current_position is None:
            raise HTTPException(status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not determine current position")
        if current_position == position:
            return {"success": True, "scan_id": scan_id, "position": position, "priority": getattr(scan, "priority", 0), "message": "Scan already at requested position"}
        scan.priority = new_priority
        scan.updated_at = datetime.utcnow()
        scan.scan_metadata = dict(scan.scan_metadata or {})
        scan.scan_metadata["position_changed_at"] = isoformat_utc(datetime.utcnow())
        scan.scan_metadata["position_changed_by"] = actor_context.get_identifier()
        scan.scan_metadata["previous_position"] = current_position
        scan.scan_metadata["new_position"] = position
        await scan_repository.update(scan)
        logger.info(f"Admin changed scan {scan_id} position from {current_position} to {position} (priority: {new_priority})")
        return {"success": True, "scan_id": scan_id, "position": position, "priority": new_priority, "previous_position": current_position, "message": f"Scan position changed from {current_position} to {position}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to change scan position: {e}", exc_info=True)
        raise HTTPException(status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to change scan position: {str(e)}")
