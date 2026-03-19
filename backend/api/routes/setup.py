"""
Setup API Routes

This module defines the FastAPI routes for the first-run setup wizard.
Handles initial database setup, admin user creation, and system validation.
"""
import os
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request
from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime, timedelta
import httpx

from sqlalchemy.exc import IntegrityError

from api.deps.actor_context import get_actor_context, ActorContext
from config.settings import settings
from infrastructure.redis.client import redis_client
from infrastructure.container import (
    get_database_health,
    get_setup_status_service,
    run_database_migrations,
)
from infrastructure.logging_config import get_logger
from domain.entities.system_state import SystemState as SystemStateEntity, SetupStatus
from domain.entities.user import User as UserEntity, UserRole
from domain.datetime_serialization import isoformat_utc
from infrastructure.container import get_system_state_repository, get_user_service

# Import new services
from api.services.setup_token_service import SetupTokenService
from api.services.setup_session_manager import SetupSessionManager
from api.services.setup_rate_limiter import SetupRateLimiter
from api.services.password_policy_service import PasswordPolicyService
from api.services.security_event_service import SecurityEventService
from domain.services.security_policy_service import SecurityPolicyService

logger = get_logger(__name__)


class SetupStatusResponse(BaseModel):
    """Response for setup status check."""
    
    setup_required: bool = Field(description="Whether setup is required")
    setup_complete: bool = Field(description="Whether setup is complete")
    database_connected: bool = Field(description="Database connection status")
    tables_exist: Dict[str, bool] = Field(description="Which tables exist")
    admin_exists: bool = Field(description="Whether admin user exists")
    system_state_exists: bool = Field(description="Whether system state exists")


class AdminUserRequest(BaseModel):
    """Request for admin user creation."""
    
    username: str = Field(min_length=2, max_length=100, description="Admin user name")
    email: EmailStr = Field(description="Admin user email")
    password: str = Field(min_length=8, max_length=128, description="Admin user password")
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        return v


class SetupInitializeRequest(BaseModel):
    """Request for system initialization."""
    
    admin_user: AdminUserRequest = Field(description="Admin user details")
    system_config: Optional[Dict[str, Any]] = Field(default={}, description="System configuration")


class SetupInitializeResponse(BaseModel):
    """Response for setup initialization."""
    
    success: bool = Field(description="Whether setup was successful")
    admin_user_id: str = Field(description="Created admin user ID")
    message: str = Field(description="Setup completion message")


class SystemHealthResponse(BaseModel):
    """Response for system health check."""
    
    database: str = Field(description="Database status")
    redis: str = Field(description="Redis status")
    docker: str = Field(description="Docker status")
    disk_space: Dict[str, Any] = Field(description="Disk space information")
    memory: Dict[str, Any] = Field(description="Memory information")


router = APIRouter(
    prefix="/api/setup",
    tags=["setup"],
    responses={
        400: {"description": "Bad Request"},
        403: {"description": "Forbidden"},
        422: {"description": "Unprocessable Entity"},
        500: {"description": "Internal Server Error"},
    },
)


@router.get(
    "/use-cases",
    summary="Get available use cases",
    description="Get all available deployment use cases with metadata for frontend display.",
    response_description="Dictionary of use cases with metadata",
)
async def get_use_cases() -> Dict[str, Any]:
    """
    Get all available use cases with metadata.
    
    Returns use cases with their configuration including:
    - Display name and description
    - Auth mode and available options
    - Feature flags and allowed features
    """
    return SecurityPolicyService.get_all_use_cases()


@router.get(
    "/status",
    response_model=SetupStatusResponse,
    summary="Get setup status",
    description="Get comprehensive setup status including table existence and admin user. Optionally validates setup session if X-Setup-Session header is provided.",
    response_description="Setup status information",
)
async def get_setup_status(
    request: Request,
    actor_context: ActorContext = Depends(get_actor_context),
    setup_session_manager: SetupSessionManager = Depends(lambda: SetupSessionManager()),
) -> SetupStatusResponse:
    """
    Get comprehensive setup status.
    
    Returns detailed information about system setup including:
    - Database connection status
    - Table existence
    - Admin user existence
    - System state existence
    - Overall setup completion status
    
    If X-Setup-Session header is provided, validates the session.
    This endpoint is accessible without authentication during setup phase.
    """
    try:
        # Get comprehensive setup status first
        setup_status = await get_setup_status_service().get_setup_status()
        
        # If setup is complete, don't require session validation (public info)
        if setup_status.get("setup_complete", False):
            return SetupStatusResponse(
                setup_required=False,
                setup_complete=True,
                database_connected=setup_status.get("database_connected", False),
                tables_exist=setup_status.get("tables", {}),
                admin_exists=setup_status.get("admin_user_exists", False),
                system_state_exists=setup_status.get("system_state_exists", False),
            )
        
        # Setup is NOT complete
        # Without session: return minimal info (only setup_complete) - no details revealed
        # With session: return full details
        session_id = request.headers.get("X-Setup-Session")
        if not session_id:
            # No session - return minimal info (only that setup is not complete)
            # This allows frontend to check if setup is done without revealing details
            return SetupStatusResponse(
                setup_required=True,
                setup_complete=False,
                database_connected=False,  # Don't reveal details
                tables_exist={},  # Don't reveal details
                admin_exists=False,  # Don't reveal details
                system_state_exists=False,  # Don't reveal details
            )
        
        # Validate session
        client_ip = request.client.host
        user_agent = request.headers.get("User-Agent", "")
        if not await setup_session_manager.validate_session(session_id, client_ip, user_agent):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired setup session"
            )
        
        # Session valid - return full details
        return SetupStatusResponse(
            setup_required=not setup_status.get("setup_complete", False),
            setup_complete=setup_status.get("setup_complete", False),
            database_connected=setup_status.get("database_connected", False),
            tables_exist=setup_status.get("tables", {}),
            admin_exists=setup_status.get("admin_user_exists", False),
            system_state_exists=setup_status.get("system_state_exists", False),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Setup status check failed: {str(e)}"
        )


@router.post(
    "/initialize",
    response_model=SetupInitializeResponse,
    summary="Initialize system setup",
    description="Perform initial system setup including database tables, admin user, and system state.",
    response_description="Setup completion result",
)
async def initialize_setup(
    request: Request,
    setup_request: SetupInitializeRequest,
    actor_context: ActorContext = Depends(get_actor_context),
    setup_session_manager: SetupSessionManager = Depends(lambda: SetupSessionManager()),
) -> SetupInitializeResponse:
    """
    Initialize system setup.
    
    Performs complete system initialization including:
    1. Creating database tables
    2. Creating admin user
    3. Creating system state record
    4. Marking setup as completed
    
    This endpoint requires a verified setup session (from token verification).
    """
    try:
        # Verify setup session
        session_id = request.headers.get("X-Setup-Session")
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Setup session required. Please verify your setup token first."
            )
        
        # Validate session
        client_ip = request.client.host
        user_agent = request.headers.get("User-Agent", "")
        if not await setup_session_manager.validate_session(session_id, client_ip, user_agent):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired setup session. Please verify your setup token again."
            )
        
        # Check if setup is already completed and locked
        repo = get_system_state_repository()
        state = await repo.get_singleton()
        if state and state.setup_locked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Setup has already been completed and locked"
            )
        
        # Validate system requirements
        db_health = await get_database_health()
        if not db_health.get("status", False):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Database connection required for setup"
            )
        
        # Create database tables
        await run_database_migrations()
        
        # Create admin user
        admin_user_id = await _create_admin_user(setup_request.admin_user)
        
        # Finalize setup atomically (creates state, locks, marks completed)
        await _finalize_setup(setup_request.system_config)
        
        # Validate scanners are available (they should already be loaded by worker/backend startup)
        # Only validate, don't refresh - if they're not there, it's a configuration issue
        try:
            import httpx
            worker_url = os.getenv("WORKER_API_URL", "http://worker:8081")
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{worker_url}/api/scanners/", timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    scanner_count = len(data.get("scanners", []))
                    if scanner_count > 0:
                        logger.info(f"Validated {scanner_count} scanners available after setup")
                    else:
                        logger.warning("No scanners found after setup - they should have been loaded on startup")
                else:
                    logger.warning(f"Could not validate scanners after setup: {response.status_code}")
        except Exception as e:
            logger.warning(f"Could not validate scanners after setup: {e}")
            # Don't fail setup - scanners will be loaded on first request
        
        # Invalidate setup session after successful setup
        await setup_session_manager.invalidate_session(session_id)
        
        return SetupInitializeResponse(
            success=True,
            admin_user_id=admin_user_id,
            message="System setup completed successfully. Database tables created, admin user created, and system configured.",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Setup initialization failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Setup initialization failed: {str(e)}"
        )


@router.post(
    "/start-token",
    summary="Generate setup token on server start",
    description="Generate setup token automatically when server starts.",
    response_description="Token generation result",
)
async def start_setup_token(
    setup_token_service: SetupTokenService = Depends(lambda: SetupTokenService()),
    security_event_service: SecurityEventService = Depends(lambda: SecurityEventService()),
) -> Dict[str, Any]:
    """
    Generate setup token on server start.
    
    This endpoint is called automatically on server startup to generate
    a new setup token with proper TTL and logging.
    """
    try:
        # Generate new setup token
        token = setup_token_service.generate_token()
        token_hash = setup_token_service.hash_token(token)
        created_at = datetime.utcnow()
        
        # Store token in database
        await setup_token_service.store_setup_token(token_hash, created_at)
        
        # Log token generation
        security_event_service.log_setup_token_generated(
            ip="server-start",
            user_agent="setup-system",
            token_hash=token_hash
        )
        
        # Print token to stdout only (not in logs)
        setup_token_service.log_token_generation(token)
        
        return {
            "success": True,
            "message": "Setup token generated successfully",
            "token_hash": token_hash,
            "created_at": isoformat_utc(created_at),
            "expires_at": isoformat_utc(
                created_at + timedelta(hours=setup_token_service.ttl_hours)
            ),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Setup token generation failed: {str(e)}"
        )


@router.get(
    "/health",
    response_model=SystemHealthResponse,
    summary="Check system health",
    description="Check the health status of all system components.",
    response_description="System health information",
)
async def check_system_health(
    actor_context: ActorContext = Depends(get_actor_context),
) -> SystemHealthResponse:
    """
    Check system health.
    
    Validates all system components are working correctly.
    """
    try:
        # Check database
        database_status = "unknown"
        try:
            db_health = await get_database_health()
            database_status = "connected" if db_health.get("status", False) else "error"
        except Exception as e:
            database_status = f"error: {str(e)}"
        
        # Check Redis
        redis_status = "unknown"
        try:
            await redis_client.connect()
            redis_status = "connected"
        except Exception as e:
            redis_status = f"error: {str(e)}"
        
        # Check Docker
        docker_status = "unknown"
        try:
            import docker
            client = docker.from_env()
            client.ping()
            docker_status = "connected"
        except Exception as e:
            docker_status = f"error: {str(e)}"
        
        # Check disk space
        disk_space = await _check_disk_space()
        
        # Check memory
        memory = await _check_memory()
        
        return SystemHealthResponse(
            database=database_status,
            redis=redis_status,
            docker=docker_status,
            disk_space=disk_space,
            memory=memory,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )


@router.post(
    "/verify",
    summary="Verify setup token",
    description="Verify setup token and create setup session.",
    response_description="Session creation result",
)
async def verify_setup_token(
    request: Request,
    setup_token_service: SetupTokenService = Depends(lambda: SetupTokenService()),
    setup_session_manager: SetupSessionManager = Depends(lambda: SetupSessionManager()),
    setup_rate_limiter: SetupRateLimiter = Depends(lambda: SetupRateLimiter()),
    security_event_service: SecurityEventService = Depends(lambda: SecurityEventService()),
) -> Dict[str, Any]:
    """
    Verify setup token and create setup session.
    
    This endpoint verifies the setup token and creates a bound setup session
    for the wizard. Uses header-based token transmission for security.
    """
    try:
        # Get client IP and User-Agent
        client_ip = request.client.host
        user_agent = request.headers.get("User-Agent", "")
        
        # Check rate limiting
        if not await setup_rate_limiter.check_and_increment(client_ip):
            security_event_service.log_brute_force_attempt(
                ip=client_ip,
                user_agent=user_agent,
                attempt_count=await setup_rate_limiter.get_attempt_counts(client_ip),
                time_window="1 hour"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many setup attempts. Please try again later."
            )
        
        # Get token from header
        token = request.headers.get("X-Setup-Token")
        if not token:
            security_event_service.log_setup_token_invalid(
                ip=client_ip,
                user_agent=user_agent,
                attempt_count=await setup_rate_limiter.get_attempt_counts(client_ip)
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Setup token required in X-Setup-Token header"
            )
        
        # Get current token info from database
        token_info = await setup_token_service.get_setup_token_info()
        if not token_info:
            security_event_service.log_setup_token_invalid(
                ip=client_ip,
                user_agent=user_agent,
                attempt_count=await setup_rate_limiter.get_attempt_counts(client_ip)
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No setup token available"
            )
        
        # Verify token with proper TTL field
        if not setup_token_service.verify_token_secure(
            token,
            token_info["token_hash"],
            token_info["created_at"]
        ):
            security_event_service.log_setup_token_invalid(
                ip=client_ip,
                user_agent=user_agent,
                attempt_count=await setup_rate_limiter.get_attempt_counts(client_ip)
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired setup token"
            )
        
        # Invalidate token after successful verification
        await setup_token_service.invalidate_setup_token()
        
        # Create bound setup session
        session_id = await setup_session_manager.create_session(
            ip=client_ip,
            user_agent=user_agent,
            token=token
        )
        
        # Log successful verification
        security_event_service.log_setup_token_verified(
            ip=client_ip,
            user_agent=user_agent,
            admin_email="pending"  # Will be set after admin creation
        )
        
        return {
            "session_id": session_id,
            "expires_in_minutes": 30,
            "message": "Setup token verified successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Setup token verification failed: {str(e)}"
        )


@router.post(
    "/admin",
    summary="Create admin user",
    description="Create admin user with password policy validation.",
    response_description="Admin creation result",
)
async def create_admin_user(
    request: Request,
    admin_data: AdminUserRequest,
    setup_session_manager: SetupSessionManager = Depends(lambda: SetupSessionManager()),
    password_policy_service: PasswordPolicyService = Depends(lambda: PasswordPolicyService()),
    security_event_service: SecurityEventService = Depends(lambda: SecurityEventService()),
) -> Dict[str, Any]:
    """
    Create admin user with enterprise password policy.
    
    This endpoint creates the admin user with Argon2 password hashing
    and comprehensive password validation.
    """
    try:
        # Get client IP and User-Agent
        client_ip = request.client.host
        user_agent = request.headers.get("User-Agent", "")
        
        # Get session ID from header
        session_id = request.headers.get("X-Setup-Session")
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Setup session required"
            )
        
        # Validate session
        if not await setup_session_manager.validate_session(session_id, client_ip, user_agent):
            expected_ip = await setup_session_manager.get_session_ip(session_id)
            expected_ua = await setup_session_manager.get_session_user_agent(session_id)
            security_event_service.log_setup_session_hijack_attempt(
                session_id=session_id,
                ip=client_ip,
                user_agent=user_agent,
                expected_ip=expected_ip,
                expected_ua=expected_ua
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or expired setup session"
            )
        
        # Validate password policy
        password_errors = password_policy_service.validate_password(admin_data.password)
        if password_errors:
            return {
                "success": False,
                "errors": password_errors,
                "password_strength": password_policy_service.get_password_strength_score(admin_data.password)
            }
        
        # Hash password with Argon2
        password_hash = password_policy_service.hash_password(admin_data.password)
        
        # Create admin user in database
        admin_user_id = await _create_admin_user_with_hash(
            username=admin_data.username,
            email=admin_data.email,
            password_hash=password_hash
        )
        
        # Complete session step
        await setup_session_manager.complete_session_step(session_id, 2)
        
        # Log admin creation
        security_event_service.log_setup_token_verified(
            ip=client_ip,
            user_agent=user_agent,
            admin_email=admin_data.email
        )
        
        return {
            "success": True,
            "admin_user_id": admin_user_id,
            "message": "Admin user created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Admin user creation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Admin user creation failed: {str(e)}"
        )


@router.post(
    "/complete",
    summary="Complete setup",
    description="Complete setup process and lock system.",
    response_description="Setup completion result",
)
async def complete_setup(
    request: Request,
    setup_session_manager: SetupSessionManager = Depends(lambda: SetupSessionManager()),
    security_event_service: SecurityEventService = Depends(lambda: SecurityEventService()),
) -> Dict[str, Any]:
    """
    Complete setup process and lock system permanently.
    
    This endpoint finalizes the setup process, creates system state,
    and locks the setup permanently.
    """
    try:
        # Get client IP and User-Agent
        client_ip = request.client.host
        user_agent = request.headers.get("User-Agent", "")
        
        # Get session ID from header
        session_id = request.headers.get("X-Setup-Session")
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Setup session required"
            )
        
        # Validate session
        if not await setup_session_manager.validate_session(session_id, client_ip, user_agent):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or expired setup session"
            )
        
        # Get session data to get admin email
        session_data = await setup_session_manager.get_session_data(session_id)
        admin_email = session_data.get("admin_email", "unknown")
        
        # Finalize setup atomically (creates state, locks, marks completed)
        await _finalize_setup({})
        
        # Invalidate session
        await setup_session_manager.invalidate_session(session_id)
        
        # Log setup completion
        setup_duration = (datetime.utcnow() - datetime.fromisoformat(session_data["created_at"])).total_seconds() / 60
        security_event_service.log_setup_completed(
            admin_email=admin_email,
            ip=client_ip,
            user_agent=user_agent,
            setup_duration_minutes=setup_duration
        )
        
        return {
            "success": True,
            "message": "Setup completed successfully. System is now locked and ready for use."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Setup completion failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Setup completion failed: {str(e)}"
        )


@router.post(
    "/skip",
    summary="Skip setup (solo / testing only)",
    description="Skip setup (solo use case or automated tests only).",
    response_description="Skip confirmation",
)
async def skip_setup(
    actor_context: ActorContext = Depends(get_actor_context),
) -> Dict[str, str]:
    """
    Skip setup. Only allowed when USE_CASE=solo. Normal installs should complete the wizard.
    """
    try:
        # Setup skip only allowed for solo use case
        if getattr(settings, "USE_CASE", "solo") != "solo":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Setup skip is only allowed for solo use case"
            )
        
        # Mark setup as completed without creating actual content
        await _mark_setup_completed()
        
        return {"message": "Setup skipped (solo use case)"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Setup skip failed: {str(e)}"
        )


# Helper functions

def _is_duplicate_key_error(e: Exception) -> bool:
    """True if exception indicates duplicate key / unique constraint violation."""
    msg = (str(e) or "").lower()
    return "duplicate key" in msg or "unique constraint" in msg or "already exists" in msg


async def _create_admin_user(admin_data: AdminUserRequest) -> str:
    """Create admin user in database. Idempotent: if username/email already exists, returns that user's id."""
    try:
        from api.services.password_policy_service import PasswordPolicyService
        password_policy_service = PasswordPolicyService()
        password_hash = password_policy_service.hash_password(admin_data.password)
        user_service = get_user_service()
        admin_user = UserEntity(
            username=admin_data.username,
            email=admin_data.email,
            password_hash=password_hash,
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,
        )
        admin_user = await user_service.create(admin_user)
        return admin_user.id
    except IntegrityError:
        pass  # fall through to duplicate handling below
    except Exception as e:
        if not _is_duplicate_key_error(e):
            logger.exception("Create admin user error: %s", e)
            raise Exception(f"Failed to create admin user: {str(e)}")
    # Duplicate username/email (e.g. double-click). Return existing user so wizard continues.
    user_service = get_user_service()
    existing = await user_service.get_by_username(admin_data.username)
    if existing:
        return existing.id
    existing = await user_service.get_by_email(admin_data.email, active_only=False)
    if existing:
        return existing.id
    raise Exception("Username or email already taken. Please use different credentials or try logging in.")


async def _create_admin_user_with_hash(username: str, email: str, password_hash: str) -> str:
    """Create admin user with pre-hashed password. Idempotent: if username/email already exists, returns that user's id."""
    try:
        user_service = get_user_service()
        admin_user = UserEntity(
            username=username,
            email=email,
            password_hash=password_hash,
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,
        )
        admin_user = await user_service.create(admin_user)
        return admin_user.id
    except IntegrityError:
        pass  # fall through to duplicate handling below
    except Exception as e:
        if not _is_duplicate_key_error(e):
            logger.exception("Create admin user (with hash) error: %s", e)
            raise Exception(f"Failed to create admin user: {str(e)}")
    # Duplicate (e.g. double-click). Return existing user id so wizard continues.
    user_service = get_user_service()
    existing = await user_service.get_by_username(username)
    if existing:
        return existing.id
    existing = await user_service.get_by_email(email, active_only=False)
    if existing:
        return existing.id
    raise Exception("Username or email already taken. Try logging in with your credentials.")


async def _finalize_setup(config: Dict[str, Any]):
    """
    Finalize setup process atomically.
    
    Creates/updates system state, locks setup permanently, and marks as completed.
    This ensures all setup steps are completed together.
    """
    try:
        # Create or update system state
        await _create_system_state(config)
        
        # Lock setup permanently
        await _lock_setup_permanently()
        
        # Mark setup as completed in Redis (for middleware)
        await _mark_setup_completed()
        
    except Exception as e:
        logger.exception("Finalize setup error: %s", e)
        raise Exception(f"Failed to finalize setup: {str(e)}")


async def _lock_setup_permanently():
    """Lock setup permanently in database."""
    try:
        repo = get_system_state_repository()
        state = await repo.get_singleton()
        if state:
            state.setup_status = SetupStatus.LOCKED
            state.setup_locked = True
            state.updated_at = datetime.utcnow()
            await repo.save(state)
    except Exception as e:
        raise Exception(f"Failed to lock setup permanently: {str(e)}")


async def _create_system_state(config: Dict[str, Any]):
    """Create or update system state record with actual system state."""
    try:
        from domain.services.security_policy_service import SecurityPolicyService
        
        # Check actual system state
        setup_status = await get_setup_status_service().get_setup_status()
        tables_exist = setup_status.get("tables", {})
        all_tables_exist = len(tables_exist) > 0 and all(tables_exist.values())
        admin_exists = setup_status.get("admin_user_exists", False)
        
        # Apply use case configuration if provided
        use_case = config.get("use_case")
        if use_case:
            use_case_config = SecurityPolicyService.apply_use_case_config(use_case)
            config.update({
                "use_case": use_case,
                "AUTH_MODE": use_case_config["AUTH_MODE"],
                "feature_flags": use_case_config["feature_flags"],
                "rate_limits": use_case_config["rate_limits"],
            })
            # Update settings for runtime
            if hasattr(settings, "USE_CASE"):
                settings.USE_CASE = use_case
            if hasattr(settings, "AUTH_MODE"):
                settings.AUTH_MODE = use_case_config["AUTH_MODE"]
            for flag_name, flag_value in use_case_config["feature_flags"].items():
                if hasattr(settings, flag_name):
                    setattr(settings, flag_name, flag_value)
        
        cfg = dict(config)
        if cfg.get("max_concurrent_jobs") is None and cfg.get("max_concurrent_scans") is not None:
            try:
                cfg["max_concurrent_jobs"] = max(1, min(50, int(cfg["max_concurrent_scans"])))
            except (TypeError, ValueError):
                cfg["max_concurrent_jobs"] = 3
        cfg.pop("scanner_timeout", None)
        cfg.pop("max_concurrent_scans", None)
        if cfg.get("max_concurrent_jobs") is None:
            cfg["max_concurrent_jobs"] = 3

        repo = get_system_state_repository()
        state = await repo.get_singleton()
        if state:
            state.setup_status = SetupStatus.COMPLETED
            state.version = "1.0.0"
            state.auth_mode = cfg.get("auth_mode", settings.AUTH_MODE)
            state.config = cfg
            state.database_initialized = all_tables_exist
            state.admin_user_created = admin_exists
            state.system_configured = True
            state.setup_completed_at = datetime.utcnow()
            state.updated_at = datetime.utcnow()
        else:
            state = SystemStateEntity()
            state.setup_status = SetupStatus.COMPLETED
            state.version = "1.0.0"
            state.auth_mode = cfg.get("auth_mode", settings.AUTH_MODE)
            state.config = cfg
            state.database_initialized = all_tables_exist
            state.admin_user_created = admin_exists
            state.system_configured = True
            state.setup_completed_at = datetime.utcnow()
            state.updated_at = datetime.utcnow()
        await repo.save(state)
    except Exception as e:
        raise Exception(f"Failed to create/update system state: {str(e)}")


async def _mark_setup_completed():
    """Mark setup as completed in Redis."""
    try:
        await redis_client.connect()
        await redis_client.set("setup:completed", "true", expire=86400 * 365)  # Expire in 1 year
        
    except Exception as e:
        raise Exception(f"Failed to mark setup as completed: {str(e)}")


async def _check_disk_space() -> Dict[str, Any]:
    """Check available disk space."""
    import shutil
    
    try:
        total, used, free = shutil.disk_usage("/")
        
        return {
            "total_gb": round(total / (1024**3), 2),
            "used_gb": round(used / (1024**3), 2),
            "free_gb": round(free / (1024**3), 2),
            "usage_percent": round((used / total) * 100, 2),
        }
    except Exception as e:
        return {"error": str(e)}


async def _check_memory() -> Dict[str, Any]:
    """Check available memory."""
    try:
        import psutil
        
        memory = psutil.virtual_memory()
        
        return {
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2),
            "usage_percent": memory.percent,
        }
    except Exception as e:
        return {"error": str(e)}
