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


def _scan_to_queue_item(scan: Scan, position: Optional[int] = None) -> Dict[str, Any]:
    """Convert Scan model to queue item format."""
    repository_name = _extract_repository_name(scan.target_url)
    branch = _extract_branch_from_config(scan.config if scan.config else {})
    
    # Map status to queue status format
    status_map = {
        "pending": "pending",
        "running": "running",
        "completed": "completed",
        "failed": "failed",
        "cancelled": "failed",  # Treat cancelled as failed for queue view
    }
    queue_status = status_map.get(scan.status.lower(), scan.status.lower())
    
    return {
        "queue_id": str(scan.id),
        "repository_name": repository_name,
        "status": queue_status,
        "scanners": scan.scanners if scan.scanners else [],
        "position": position,
        "created_at": scan.created_at.isoformat() if scan.created_at else None,
        "branch": branch,
        "scan_id": str(scan.id),  # For compatibility
    }


def _scan_to_my_scan_item(scan: Scan, position: Optional[int] = None) -> Dict[str, Any]:
    """Convert Scan model to my-scans item format."""
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
    description="Get all scans in queue view format. Shows scans from database filtered by status (pending, running, completed, failed). Admin users see all scans, regular users see only their own.",
)
async def get_queue(
    limit: int = Query(100, ge=1, le=1000, description="Limit results"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (pending, running, completed, failed)"),
    actor_context: ActorContext = Depends(get_actor_context),
) -> Dict[str, Any]:
    """
    Get queue status with scans.
    
    Returns scans from PostgreSQL database in queue format.
    - Admin users: See all scans
    - Regular users: See only their own scans (filtered by user_id or session_id)
    """
    try:
        is_admin = await _is_admin_user(actor_context)
        await db_adapter.ensure_initialized()
        
        async with db_adapter.async_session() as session:
            # Build query
            query = select(Scan)
            
            # Filter by user if not admin
            if not is_admin:
                # Regular users: only see their own scans
                if actor_context.is_authenticated and actor_context.user_id:
                    try:
                        from uuid import UUID
                        user_uuid = UUID(actor_context.user_id)
                        query = query.where(Scan.user_id == user_uuid)
                    except (ValueError, TypeError):
                        return {"items": [], "queue_length": 0, "max_queue_length": 100}
                elif actor_context.session_id:
                    # Guest sessions: filter by session_id in metadata
                    from sqlalchemy import text
                    query = query.where(
                        text("scans.scan_metadata->>'session_id' = :session_id")
                    ).params(session_id=actor_context.session_id)
                else:
                    return {"items": [], "queue_length": 0, "max_queue_length": 100}
            
            # Filter by status if provided
            if status_filter:
                query = query.where(Scan.status.ilike(f"%{status_filter}%"))
            else:
                # Default: show pending, running, completed, failed
                query = query.where(
                    Scan.status.in_(["pending", "running", "completed", "failed", "cancelled"])
                )
            
            # Order by created_at (oldest first for queue position)
            query = query.order_by(Scan.created_at.asc())
            
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
            items = []
            for idx, scan in enumerate(scans):
                # Calculate position only for pending/running scans
                position = None
                if scan.status.lower() in ["pending", "running"]:
                    # Count how many scans are before this one with same status
                    position_query = select(func.count(Scan.id)).where(
                        and_(
                            Scan.status == scan.status,
                            Scan.created_at < scan.created_at
                        )
                    )
                    pos_result = await session.execute(position_query)
                    position = (pos_result.scalar() or 0) + 1
                
                items.append(_scan_to_queue_item(scan, position))
            
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
            
            # Order by created_at (newest first)
            query = query.order_by(Scan.created_at.desc())
            
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
                            Scan.created_at < scan.created_at
                        )
                    )
                    pos_result = await session.execute(position_query)
                    position = (pos_result.scalar() or 0) + 1
                
                items.append(_scan_to_my_scan_item(scan, position))
            
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
                        Scan.created_at < scan.created_at
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
