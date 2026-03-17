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
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from api.deps.actor_context import get_actor_context, ActorContext
from infrastructure.database.adapter import db_adapter
from infrastructure.database.models import Scan
from infrastructure.logging_config import get_logger
from domain.services.scanner_duration_service import ScannerDurationService

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


async def _scan_to_queue_item(scan: Scan, position: Optional[int] = None, show_branch: bool = False) -> Dict[str, Any]:
    """
    Convert Scan model to queue item format.
    
    Args:
        scan: Scan model
        position: Position in queue
        show_branch: Whether to include branch name (only for authenticated users, not guests)
    """
    repository_name = _extract_repository_name(scan.target_url)
    branch = _extract_branch_from_config(scan.config if scan.config else {}) if show_branch else None
    
    # Map status to queue status format
    status_map = {
        "pending": "pending",
        "running": "running",
        "completed": "completed",
        "failed": "failed",
        "cancelled": "failed",  # Treat cancelled as failed for queue view
    }
    queue_status = status_map.get(scan.status.lower(), scan.status.lower())
    
    # Calculate estimated time for pending/running scans
    estimated_time_seconds = None
    if queue_status in ["pending", "running"] and scan.scanners:
        estimated_time_seconds = await ScannerDurationService.get_estimated_time(scan.scanners)
    
    # Get actual duration for completed/running scans
    duration_seconds = None
    if scan.duration is not None:
        duration_seconds = scan.duration
    elif scan.started_at and scan.completed_at:
        duration_seconds = int((scan.completed_at - scan.started_at).total_seconds())
    elif scan.started_at and queue_status == "running":
        # Calculate current duration for running scans
        from datetime import datetime
        duration_seconds = int((datetime.utcnow() - scan.started_at).total_seconds())
    
    result = {
        "queue_id": str(scan.id),
        "repository_name": repository_name,
        "status": queue_status,
        "scanners": scan.scanners if scan.scanners else [],
        "position": position,
        "created_at": scan.created_at.isoformat() if scan.created_at else None,
        "scan_id": str(scan.id),  # For compatibility
        "estimated_time_seconds": estimated_time_seconds,
        "duration_seconds": duration_seconds,
    }
    
    # Only include branch if show_branch is True (for authenticated users)
    if show_branch and branch:
        result["branch"] = branch
    
    return result


async def _scan_to_my_scan_item(scan: Scan, position: Optional[int] = None) -> Dict[str, Any]:
    """
    Convert Scan model to my-scans item format.
    
    This is for "My Scans" endpoint, so branch is always shown (user's own scans).
    """
    repository_name = _extract_repository_name(scan.target_url)
    branch = _extract_branch_from_config(scan.config if scan.config else {})
    
    # Extract commit hash from metadata or config
    commit_hash = None
    if scan.scan_metadata:
        commit_hash = scan.scan_metadata.get("commit_hash") or scan.scan_metadata.get("commit")
    if not commit_hash and scan.config:
        commit_hash = scan.config.get("commit_hash") or scan.config.get("commit")
    
    status_map = {
        "pending": "pending",
        "running": "running",
        "completed": "completed",
        "failed": "failed",
        "cancelled": "failed",
    }
    queue_status = status_map.get(scan.status.lower(), scan.status.lower())
    
    # Calculate estimated time for pending/running scans
    estimated_time_seconds = None
    if queue_status in ["pending", "running"] and scan.scanners:
        estimated_time_seconds = await ScannerDurationService.get_estimated_time(scan.scanners)
    
    # Get actual duration for completed/running scans
    duration_seconds = None
    if scan.duration is not None:
        duration_seconds = scan.duration
    elif scan.started_at and scan.completed_at:
        duration_seconds = int((scan.completed_at - scan.started_at).total_seconds())
    elif scan.started_at and queue_status == "running":
        # Calculate current duration for running scans
        from datetime import datetime
        duration_seconds = int((datetime.utcnow() - scan.started_at).total_seconds())
    
    return {
        "queue_id": str(scan.id),
        "repository_url": scan.target_url,
        "repository_name": repository_name,
        "branch": branch,
        "commit_hash": commit_hash,
        "status": queue_status,
        "scan_id": str(scan.id),
        "position": position,
        "created_at": scan.created_at.isoformat() if scan.created_at else None,
        "started_at": scan.started_at.isoformat() if scan.started_at else None,
        "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
        "scanners": scan.scanners if scan.scanners else [],
        "estimated_time_seconds": estimated_time_seconds,
        "duration_seconds": duration_seconds,
    }


async def _is_admin_user(actor_context: ActorContext) -> bool:
    """Check if the current user is an admin."""
    if not actor_context.is_authenticated or not actor_context.user_id:
        return False
    
    try:
        await db_adapter.ensure_initialized()
        
        async with db_adapter.async_session() as session:
            from uuid import UUID
            from infrastructure.database.models import User, UserRoleEnum
            
            user_uuid = UUID(actor_context.user_id)
            result = await session.execute(
                select(User).where(User.id == user_uuid)
            )
            user = result.scalar_one_or_none()
            
            if user and user.role == UserRoleEnum.ADMIN:
                return True
    except Exception as e:
        logger.warning(f"Failed to check admin status: {e}")
    
    return False


@router.get(
    "/",
    summary="Get queue status",
    description="Get all scans in queue view format (anonymized). Shows all scans from database filtered by status (pending, running, completed, failed). Everyone sees all scans anonymized.",
)
async def get_queue(
    limit: int = Query(100, ge=1, le=1000, description="Limit results"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (pending, running, completed, failed)"),
    actor_context: ActorContext = Depends(get_actor_context),
) -> Dict[str, Any]:
    """
    Get queue status with scans (Public Queue - anonymized).
    
    Returns scans from PostgreSQL database in queue format.
    - Everyone (guests, users, admins): See all scans anonymized
    - No user filtering - this is the public queue view
    - User-specific scans are available via /api/queue/my-scans
    """
    try:
        is_admin = await _is_admin_user(actor_context)
        await db_adapter.ensure_initialized()
        
        async with db_adapter.async_session() as session:
            # Build query
            query = select(Scan)
            
            # Public Queue: Show ALL scans (anonymized) for everyone
            # No user filter - everyone sees all scans in the public queue
            # User-specific scans are available via /api/queue/my-scans
            
            # Filter by status if provided
            if status_filter:
                query = query.where(Scan.status.ilike(f"%{status_filter}%"))
            else:
                # Default: show only active queue (pending + running)
                query = query.where(Scan.status.in_(["pending", "running"]))
            
            # Order by priority (higher first), then created_at (oldest first)
            query = query.order_by(Scan.priority.desc(), Scan.created_at.asc())
            
            # Limit results
            query = query.limit(limit)
            
            result = await session.execute(query)
            scans = result.scalars().all()
            
            # Count total queue length (pending + running)
            count_query = select(func.count(Scan.id)).where(
                Scan.status.in_(["pending", "running"])
            )
            count_result = await session.execute(count_query)
            queue_length = count_result.scalar() or 0
            
            # Convert to queue items
            # Public queue: Never show branch (anonymized for all users, including authenticated)
            # Only "My Scans" shows branch (because those are the user's own scans)
            items = []
            for idx, scan in enumerate(scans):
                # Calculate position only for pending/running scans
                position = None
                if scan.status.lower() in ["pending", "running"]:
                    # Count how many scans are before this one (higher priority or same priority but earlier created_at)
                    position_query = select(func.count(Scan.id)).where(
                        and_(
                            Scan.status == scan.status,
                            or_(
                                Scan.priority > scan.priority,
                                and_(
                                    Scan.priority == scan.priority,
                                    Scan.created_at < scan.created_at
                                )
                            )
                        )
                    )
                    pos_result = await session.execute(position_query)
                    position = (pos_result.scalar() or 0) + 1
                
                # Public queue: never show branch (anonymized)
                items.append(await _scan_to_queue_item(scan, position, show_branch=False))
            
            return {
                "items": items,
                "queue_length": queue_length,
                "max_queue_length": 100,  # TODO: Make configurable
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
) -> Dict[str, Any]:
    """
    Get scans for the current user/session.
    
    Returns scans from PostgreSQL database filtered by user_id or session_id.
    """
    try:
        user_identifier = actor_context.get_identifier()
        await db_adapter.ensure_initialized()
        
        async with db_adapter.async_session() as session:
            # Build query - filter by user_id or session_id in metadata
            query = select(Scan)
            
            # For authenticated users: match by user_id
            if actor_context.is_authenticated and actor_context.user_id:
                try:
                    from uuid import UUID
                    user_uuid = UUID(actor_context.user_id)
                    query = query.where(Scan.user_id == user_uuid)
                except (ValueError, TypeError):
                    # Invalid UUID format
                    return {"scans": []}
            else:
                # For guest sessions: match by session_id in metadata
                if actor_context.session_id:
                    # Filter scans where metadata contains session_id
                    # PostgreSQL JSON query: scans.metadata->>'session_id' = session_id
                    from sqlalchemy import text
                    query = query.where(
                        text("scans.scan_metadata->>'session_id' = :session_id")
                    ).params(session_id=actor_context.session_id)
                else:
                    # No session_id available
                    return {"scans": []}
            
            # Filter by status if provided
            if status_filter:
                query = query.where(Scan.status.ilike(f"%{status_filter}%"))
            
            # Order by priority (higher first), then created_at (newest first)
            query = query.order_by(Scan.priority.desc(), Scan.created_at.desc())
            
            # Limit results
            query = query.limit(limit)
            
            result = await session.execute(query)
            scans = result.scalars().all()
            
            # Convert to my-scans items
            items = []
            for idx, scan in enumerate(scans):
                # Calculate position for pending/running scans
                position = None
                if scan.status.lower() in ["pending", "running"]:
                    position_query = select(func.count(Scan.id)).where(
                        and_(
                            Scan.status == scan.status,
                            or_(
                                Scan.priority > scan.priority,
                                and_(
                                    Scan.priority == scan.priority,
                                    Scan.created_at < scan.created_at
                                )
                            )
                        )
                    )
                    pos_result = await session.execute(position_query)
                    position = (pos_result.scalar() or 0) + 1
                
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
) -> Dict[str, Any]:
    """
    Get queue status for a specific scan.
    
    Returns scan status in queue format from PostgreSQL database.
    """
    try:
        await db_adapter.ensure_initialized()
        
        async with db_adapter.async_session() as session:
            from uuid import UUID
            
            try:
                scan_uuid = UUID(scan_id)
            except ValueError:
                raise HTTPException(
                    status_code=fastapi_status.HTTP_400_BAD_REQUEST,
                    detail="Invalid scan ID format"
                )
            
            query = select(Scan).where(Scan.id == scan_uuid)
            result = await session.execute(query)
            scan = result.scalar_one_or_none()
            
            if not scan:
                raise HTTPException(
                    status_code=fastapi_status.HTTP_404_NOT_FOUND,
                    detail=f"Scan {scan_id} not found"
                )
            
            # Calculate position if pending/running
            position = None
            if scan.status.lower() in ["pending", "running"]:
                position_query = select(func.count(Scan.id)).where(
                    and_(
                        Scan.status == scan.status,
                        or_(
                            Scan.priority > scan.priority,
                            and_(
                                Scan.priority == scan.priority,
                                Scan.created_at < scan.created_at
                            )
                        )
                    )
                )
                pos_result = await session.execute(position_query)
                position = (pos_result.scalar() or 0) + 1
            
            status_map = {
                "pending": "pending",
                "running": "running",
                "completed": "completed",
                "failed": "failed",
                "cancelled": "failed",
            }
            queue_status = status_map.get(scan.status.lower(), scan.status.lower())
            
            return {
                "queue_id": str(scan.id),
                "scan_id": str(scan.id),
                "repository_name": _extract_repository_name(scan.target_url),
                "status": queue_status,
                "position": position,
                "created_at": scan.created_at.isoformat() if scan.created_at else None,
                "started_at": scan.started_at.isoformat() if scan.started_at else None,
                "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
                "scanners": scan.scanners if scan.scanners else [],
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
) -> Dict[str, Any]:
    """
    Delete a scan from the queue.
    
    - **User**: Can only delete own scans (if pending)
    - **Admin**: Can delete any scan
    - Removes scan from Redis queue and sets status to 'cancelled' in database
    """
    try:
        await db_adapter.ensure_initialized()
        is_admin = await _is_admin_user(actor_context)
        
        async with db_adapter.async_session() as session:
            from uuid import UUID
            from infrastructure.services.queue_service import QueueService
            from application.services.scan_orchestration_service import ScanOrchestrationService
            
            try:
                scan_uuid = UUID(scan_id)
            except ValueError:
                raise HTTPException(
                    status_code=fastapi_status.HTTP_400_BAD_REQUEST,
                    detail="Invalid scan ID format"
                )
            
            # Get scan
            query = select(Scan).where(Scan.id == scan_uuid)
            result = await session.execute(query)
            scan = result.scalar_one_or_none()
            
            if not scan:
                raise HTTPException(
                    status_code=fastapi_status.HTTP_404_NOT_FOUND,
                    detail=f"Scan {scan_id} not found"
                )
            
            # Check permissions
            if not is_admin:
                # Regular user: can only delete own scans
                user_identifier = actor_context.get_identifier()
                
                # Check if scan belongs to user
                if actor_context.is_authenticated and actor_context.user_id:
                    try:
                        user_uuid = UUID(actor_context.user_id)
                        if scan.user_id != user_uuid:
                            raise HTTPException(
                                status_code=fastapi_status.HTTP_403_FORBIDDEN,
                                detail="You can only delete your own scans"
                            )
                    except (ValueError, TypeError):
                        raise HTTPException(
                            status_code=fastapi_status.HTTP_403_FORBIDDEN,
                            detail="Invalid user context"
                        )
                elif actor_context.session_id:
                    # Guest session: check session_id in metadata
                    scan_session_id = scan.scan_metadata.get("session_id") if scan.scan_metadata else None
                    if scan_session_id != actor_context.session_id:
                        raise HTTPException(
                            status_code=fastapi_status.HTTP_403_FORBIDDEN,
                            detail="You can only delete your own scans"
                        )
                else:
                    raise HTTPException(
                        status_code=fastapi_status.HTTP_403_FORBIDDEN,
                        detail="Authentication required"
                    )
                
                # Regular users can only delete pending scans
                if scan.status.lower() not in ["pending"]:
                    raise HTTPException(
                        status_code=fastapi_status.HTTP_400_BAD_REQUEST,
                        detail="You can only delete pending scans. Use cancel for running scans."
                    )
            
            # Remove from Redis queue
            queue_service = QueueService()
            removed_from_queue = await queue_service.remove_scan_from_queue(scan_id)
            
            if scan.status.lower() == "running":
                await queue_service.signal_worker_cancel(scan_id)
                orchestration_service = ScanOrchestrationService()
                await orchestration_service.cancel_scan(scan_id)
            
            # Update scan status to cancelled
            scan.status = "cancelled"
            scan.updated_at = datetime.utcnow()
            
            # Add cancellation metadata
            if not scan.scan_metadata:
                scan.scan_metadata = {}
            scan.scan_metadata["cancelled_at"] = datetime.utcnow().isoformat()
            scan.scan_metadata["cancelled_by"] = actor_context.get_identifier()
            
            await session.commit()
            
            logger.info(f"Deleted scan {scan_id} from queue (removed from Redis: {removed_from_queue})")
            
            return {
                "success": True,
                "scan_id": scan_id,
                "removed_from_queue": removed_from_queue,
                "status": "cancelled",
                "message": "Scan deleted from queue successfully"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete scan from queue: {e}", exc_info=True)
        raise HTTPException(
            status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete scan from queue: {str(e)}"
        )


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
    description="Change the position of a scan in the queue by setting its priority. Admin only. Higher priority = earlier in queue.",
)
async def change_scan_position(
    scan_id: str,
    position: int = Query(..., ge=1, description="New position in queue (1 = first)"),
    actor_context: ActorContext = Depends(get_actor_context),
) -> Dict[str, Any]:
    """
    Change the position of a scan in the queue.
    
    - **Admin only**
    - Sets priority based on position (higher position = higher priority)
    - Only works for pending scans
    - Position 1 = highest priority (will be processed first)
    """
    try:
        is_admin = await _is_admin_user(actor_context)
        if not is_admin:
            raise HTTPException(
                status_code=fastapi_status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        
        await db_adapter.ensure_initialized()
        
        async with db_adapter.async_session() as session:
            from uuid import UUID
            
            try:
                scan_uuid = UUID(scan_id)
            except ValueError:
                raise HTTPException(
                    status_code=fastapi_status.HTTP_400_BAD_REQUEST,
                    detail="Invalid scan ID format"
                )
            
            # Get scan
            query = select(Scan).where(Scan.id == scan_uuid)
            result = await session.execute(query)
            scan = result.scalar_one_or_none()
            
            if not scan:
                raise HTTPException(
                    status_code=fastapi_status.HTTP_404_NOT_FOUND,
                    detail=f"Scan {scan_id} not found"
                )
            
            # Only allow position change for pending scans
            if scan.status.lower() != "pending":
                raise HTTPException(
                    status_code=fastapi_status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot change position for scan with status '{scan.status}'. Only pending scans can be reordered."
                )
            
            # Get all pending scans ordered by current priority
            pending_query = select(Scan).where(
                Scan.status == "pending"
            ).order_by(Scan.priority.desc(), Scan.created_at.asc())
            
            pending_result = await session.execute(pending_query)
            pending_scans = pending_result.scalars().all()
            
            if position > len(pending_scans):
                raise HTTPException(
                    status_code=fastapi_status.HTTP_400_BAD_REQUEST,
                    detail=f"Position {position} is out of range. There are only {len(pending_scans)} pending scans."
                )
            
            # Calculate new priority
            # Position 1 = highest priority (1000), position 2 = 999, etc.
            # This ensures higher priority values = earlier in queue
            max_priority = 1000
            new_priority = max_priority - (position - 1)
            
            # If there are other scans with the same priority, we need to adjust
            # Find the target scan's current position
            current_position = None
            for idx, s in enumerate(pending_scans):
                if s.id == scan_uuid:
                    current_position = idx + 1
                    break
            
            if current_position is None:
                raise HTTPException(
                    status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not determine current position"
                )
            
            # If moving to same position, no change needed
            if current_position == position:
                return {
                    "success": True,
                    "scan_id": scan_id,
                    "position": position,
                    "priority": scan.priority,
                    "message": "Scan already at requested position"
                }
            
            # Update priority
            scan.priority = new_priority
            scan.updated_at = datetime.utcnow()
            
            # Add metadata about position change
            if not scan.scan_metadata:
                scan.scan_metadata = {}
            scan.scan_metadata["position_changed_at"] = datetime.utcnow().isoformat()
            scan.scan_metadata["position_changed_by"] = actor_context.get_identifier()
            scan.scan_metadata["previous_position"] = current_position
            scan.scan_metadata["new_position"] = position
            
            await session.commit()
            
            logger.info(f"Admin changed scan {scan_id} position from {current_position} to {position} (priority: {new_priority})")
            
            return {
                "success": True,
                "scan_id": scan_id,
                "position": position,
                "priority": new_priority,
                "previous_position": current_position,
                "message": f"Scan position changed from {current_position} to {position}"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to change scan position: {e}", exc_info=True)
        raise HTTPException(
            status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to change scan position: {str(e)}"
        )
