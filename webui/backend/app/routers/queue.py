"""
Queue Routes
"""
import os
from fastapi import APIRouter, HTTPException, Request
from app.services import get_queue_service
from app.services.session_service import get_session_service

router = APIRouter()

# Will be injected from main
IS_PRODUCTION = None


def init_queue_router(is_production: bool):
    """Initialize router with environment"""
    global IS_PRODUCTION
    IS_PRODUCTION = is_production


@router.post("/api/queue/add")
async def add_to_queue(
    repository_url: str,
    branch: str = None,
    http_request: Request = None,
):
    """Add scan to queue (Production only)"""
    if not IS_PRODUCTION:
        raise HTTPException(status_code=400, detail="Queue system only available in production mode")
    
    # Get session ID
    if not http_request:
        raise HTTPException(status_code=500, detail="Request object not available")
    
    session_id = getattr(http_request.state, "session_id", None)
    if not session_id:
        raise HTTPException(status_code=401, detail="Session required")
    
    # Check rate limits
    session_service = await get_session_service()
    allowed, error_msg = await session_service.check_rate_limit(session_id)
    if not allowed:
        raise HTTPException(status_code=429, detail=error_msg)
    
    # Validate Git URL
    from app.services.git_service import is_git_url
    if not is_git_url(repository_url):
        raise HTTPException(status_code=400, detail="Only Git repository URLs are allowed")
    
    # Add to queue
    queue_service = await get_queue_service()
    result = await queue_service.add_scan_to_queue(
        session_id=session_id,
        repository_url=repository_url,
        branch=branch,
        commit_hash=None,  # TODO: Extract from Git if needed
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result.get("message", "Failed to add to queue"))
    
    # Increment scan count
    await session_service.increment_scan_count(session_id)
    
    return result


@router.get("/api/queue")
async def get_queue(limit: int = 100):
    """Get public queue (anonymized) - Queue is always enabled"""
    queue_service = await get_queue_service()
    items = await queue_service.get_public_queue(limit=limit)
    queue_length = await queue_service.get_queue_length()
    
    return {
        "items": items,  # REST Standard: collections use "items"
        "queue_length": queue_length,
        "max_queue_length": int(os.getenv("MAX_QUEUE_LENGTH", "1000")),
    }


@router.get("/api/queue/{queue_id}/status")
async def get_queue_status(queue_id: str, http_request: Request = None):
    """Get status of a queue item - Queue is always enabled"""
    queue_service = await get_queue_service()
    queue_item = await queue_service.get_queue_status(queue_id)
    
    if not queue_item:
        raise HTTPException(status_code=404, detail="Queue item not found")
    
    # Check if user owns this queue item (if session available)
    session_id = getattr(http_request.state, "session_id", None) if http_request else None
    if session_id and queue_item.get("session_id") == session_id:
        # Return full details for owner
        return queue_item
    else:
        # Return anonymized version for others
        return {
            "queue_id": queue_item["queue_id"],
            "repository_name": queue_item["repository_name"],
            "status": queue_item["status"],
            "position": queue_item.get("position"),
            "created_at": queue_item.get("created_at"),
        }


@router.get("/api/queue/my-scans")
async def get_my_scans(http_request: Request):
    """Get queue items for current session - Queue is always enabled"""
    session_id = getattr(http_request.state, "session_id", None)
    if not session_id:
        raise HTTPException(status_code=401, detail="Session required")
    
    queue_service = await get_queue_service()
    scans = await queue_service.get_user_queue(session_id)
    
    return {"scans": scans}


@router.get("/api/statistics")
async def get_statistics():
    """Get aggregated statistics"""
    if not IS_PRODUCTION:
        return {"message": "Statistics only available in production mode"}
    
    from app.database import get_database
    db = get_database()
    # Database is already initialized by startup event, but ensure it's ready
    await db.initialize()
    
    stats = await db.get_statistics()
    return stats
