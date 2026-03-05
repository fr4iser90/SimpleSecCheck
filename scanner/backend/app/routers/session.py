"""
Session Routes
"""
from fastapi import APIRouter, Request
from app.services import get_session_service

router = APIRouter()

# Will be injected from main
IS_PRODUCTION = None


def init_session_router(is_production: bool):
    """Initialize router with environment"""
    global IS_PRODUCTION
    IS_PRODUCTION = is_production


@router.get("/api/session")
async def get_session_info(http_request: Request):
    """Get current session information"""
    if not IS_PRODUCTION:
        return {"session_id": None, "mode": "development"}
    
    session_id = getattr(http_request.state, "session_id", None)
    if not session_id:
        return {"session_id": None, "mode": "production"}
    
    session_service = await get_session_service()
    session = await session_service.validate_session(session_id)
    
    if not session:
        return {"session_id": None, "mode": "production", "valid": False}
    
    return {
        "session_id": session_id,
        "mode": "production",
        "valid": True,
        "scans_requested": session.get("scans_requested", 0),
        "rate_limit_scans": session.get("rate_limit_scans", 10),
    }
