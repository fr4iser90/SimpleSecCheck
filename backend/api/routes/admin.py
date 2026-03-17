"""
Admin API Routes

Handles admin-only operations like system configuration updates.
"""
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from pydantic import BaseModel, EmailStr, Field

from api.deps.actor_context import get_admin_user, ActorContext
from infrastructure.database.adapter import db_adapter
from infrastructure.database.models import SystemState
from domain.services.audit_log_service import AuditLogService
from domain.services.scanner_duration_service import ScannerDurationService
from domain.services.target_permission_policy import ALL_SCAN_FEATURE_FLAG_KEYS
from sqlalchemy import select
from datetime import datetime

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        500: {"description": "Internal Server Error"},
    },
)


class SMTPConfigRequest(BaseModel):
    """Request for SMTP configuration update."""
    
    enabled: bool = Field(description="Enable SMTP")
    host: str = Field(description="SMTP host")
    port: int = Field(description="SMTP port")
    user: str = Field(description="SMTP username/email")
    password: str = Field(description="SMTP password")
    use_tls: bool = Field(default=True, description="Use TLS")
    from_email: str = Field(description="From email address")
    from_name: str = Field(description="From name")


class SMTPConfigResponse(BaseModel):
    """Response for SMTP configuration."""
    
    enabled: bool
    host: str
    port: int
    user: str
    password: str = Field(description="Password (masked)")
    use_tls: bool
    from_email: str
    from_name: str


class SystemConfigResponse(BaseModel):
    """Response for system configuration."""
    
    auth_mode: str
    scanner_timeout: int
    max_concurrent_scans: int
    smtp: Optional[Dict[str, Any]] = None


class AuthConfigResponse(BaseModel):
    """Auth config: AUTH_MODE = login mechanism; ACCESS_MODE = who may use the system; allow_self_registration; bulk_scan_allow_guests."""
    auth_mode: str = Field(description="Authentication mode (login mechanism): free | basic | jwt")
    access_mode: str = Field(description="Who may use the system: public | mixed | private")
    allow_self_registration: bool = Field(description="Allow users to self-register (sign up)")
    bulk_scan_allow_guests: bool = Field(default=False, description="Allow guests to use bulk scan (admin override). Default: only logged-in users.")


class AuthConfigRequest(BaseModel):
    """Request to update auth configuration."""
    auth_mode: Optional[str] = Field(None, description="free | basic | jwt")
    access_mode: Optional[str] = Field(None, description="public | mixed | private")
    allow_self_registration: Optional[bool] = None
    bulk_scan_allow_guests: Optional[bool] = Field(None, description="Allow guests to use bulk scan (admin override)")


class QueueConfigResponse(BaseModel):
    """Queue strategy and default priorities."""
    queue_strategy: str = Field(description="fifo | priority | round_robin")
    priority_admin: int = Field(default=10, description="Default priority for admin scans")
    priority_user: int = Field(default=5, description="Default priority for user scans")
    priority_guest: int = Field(default=1, description="Default priority for guest scans")


class QueueConfigRequest(BaseModel):
    """Request to update queue config."""
    queue_strategy: Optional[str] = Field(None, description="fifo | priority | round_robin")
    priority_admin: Optional[int] = None
    priority_user: Optional[int] = None
    priority_guest: Optional[int] = None


@router.get("/config", response_model=SystemConfigResponse)
async def get_system_config(
    actor_context: ActorContext = Depends(get_admin_user),
) -> SystemConfigResponse:
    """
    Get current system configuration.
    
    Requires admin privileges.
    """
    try:
        async with db_adapter.async_session() as session:
            result = await session.execute(select(SystemState).limit(1))
            system_state = result.scalar_one_or_none()
            
            if not system_state:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="System state not found"
                )
            
            config = system_state.config or {}
            smtp_config = config.get("smtp")
            
            # Mask password in response
            if smtp_config and "password" in smtp_config:
                smtp_config = smtp_config.copy()
                smtp_config["password"] = "***" if smtp_config.get("password") else ""
            
            return SystemConfigResponse(
                auth_mode=system_state.auth_mode,
                scanner_timeout=config.get("scanner_timeout", 3600),
                max_concurrent_scans=config.get("max_concurrent_scans", 5),
                smtp=smtp_config
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system config: {str(e)}"
        )


@router.get("/config/auth", response_model=AuthConfigResponse)
async def get_auth_config(
    actor_context: ActorContext = Depends(get_admin_user),
) -> AuthConfigResponse:
    """
    Get auth configuration (who may access, registration).
    Requires admin privileges.
    """
    try:
        async with db_adapter.async_session() as session:
            result = await session.execute(select(SystemState).limit(1))
            system_state = result.scalar_one_or_none()
            if not system_state:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="System state not found"
                )
            config = system_state.config or {}
            auth_cfg = config.get("auth") or {}
            if not isinstance(auth_cfg, dict):
                auth_cfg = {}
            return AuthConfigResponse(
                auth_mode=getattr(system_state, "auth_mode", None) or config.get("AUTH_MODE", "free"),
                access_mode=auth_cfg.get("access_mode") or ("public" if (getattr(system_state, "auth_mode", None) or config.get("AUTH_MODE")) == "free" else "private"),
                allow_self_registration=auth_cfg.get("allow_self_registration", False),
                bulk_scan_allow_guests=auth_cfg.get("bulk_scan_allow_guests", False),
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get auth config: {str(e)}"
        )


@router.put("/config/auth", response_model=AuthConfigResponse)
async def update_auth_config(
    request: Request,
    body: AuthConfigRequest,
    actor_context: ActorContext = Depends(get_admin_user),
) -> AuthConfigResponse:
    """
    Update auth configuration.
    Requires admin privileges.
    """
    try:
        async with db_adapter.async_session() as session:
            result = await session.execute(select(SystemState).limit(1))
            system_state = result.scalar_one_or_none()
            if not system_state:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="System state not found"
                )
            config = system_state.config or {}
            if "auth" not in config:
                config["auth"] = {}
            auth_cfg = config["auth"]
            if body.auth_mode is not None:
                system_state.auth_mode = body.auth_mode
                config["AUTH_MODE"] = body.auth_mode
            if body.access_mode is not None:
                auth_cfg["access_mode"] = body.access_mode
            if body.allow_self_registration is not None:
                auth_cfg["allow_self_registration"] = body.allow_self_registration
            if body.bulk_scan_allow_guests is not None:
                auth_cfg["bulk_scan_allow_guests"] = body.bulk_scan_allow_guests
            config["auth"] = auth_cfg
            system_state.config = config
            system_state.updated_at = datetime.utcnow()
            await session.commit()
            from config.settings import load_settings_from_database, settings as app_settings
            await load_settings_from_database(app_settings)
            await AuditLogService.log_event(
                user_id=actor_context.user_id,
                user_email=actor_context.email,
                action_type="AUTH_CONFIG_CHANGED",
                target="auth_config",
                details={"access_mode": auth_cfg.get("access_mode"), "allow_self_registration": auth_cfg.get("allow_self_registration"), "bulk_scan_allow_guests": auth_cfg.get("bulk_scan_allow_guests"), "auth_mode": system_state.auth_mode},
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent")
            )
            return AuthConfigResponse(
                auth_mode=system_state.auth_mode,
                access_mode=auth_cfg.get("access_mode") or ("public" if system_state.auth_mode == "free" else "private"),
                allow_self_registration=auth_cfg.get("allow_self_registration", False),
                bulk_scan_allow_guests=auth_cfg.get("bulk_scan_allow_guests", False),
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update auth config: {str(e)}"
        )


@router.get("/config/queue", response_model=QueueConfigResponse)
async def get_queue_config(
    actor_context: ActorContext = Depends(get_admin_user),
) -> QueueConfigResponse:
    """Get queue strategy and priority defaults. Requires admin."""
    try:
        async with db_adapter.async_session() as session:
            result = await session.execute(select(SystemState).limit(1))
            system_state = result.scalar_one_or_none()
            if not system_state:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="System state not found")
            config = system_state.config or {}
            queue_cfg = config.get("queue") or {}
            from config.settings import get_settings
            s = get_settings()
            return QueueConfigResponse(
                queue_strategy=queue_cfg.get("queue_strategy") or getattr(s, "QUEUE_STRATEGY", "fifo"),
                priority_admin=int(queue_cfg.get("priority_admin", getattr(s, "QUEUE_PRIORITY_ADMIN", 10))),
                priority_user=int(queue_cfg.get("priority_user", getattr(s, "QUEUE_PRIORITY_USER", 5))),
                priority_guest=int(queue_cfg.get("priority_guest", getattr(s, "QUEUE_PRIORITY_GUEST", 1))),
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/config/queue", response_model=QueueConfigResponse)
async def update_queue_config(
    body: QueueConfigRequest,
    actor_context: ActorContext = Depends(get_admin_user),
) -> QueueConfigResponse:
    """Update queue strategy and priority defaults. Requires admin."""
    try:
        async with db_adapter.async_session() as session:
            result = await session.execute(select(SystemState).limit(1))
            system_state = result.scalar_one_or_none()
            if not system_state:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="System state not found")
            config = system_state.config or {}
            if "queue" not in config:
                config["queue"] = {}
            q = config["queue"]
            if body.queue_strategy is not None and body.queue_strategy in ("fifo", "priority", "round_robin"):
                q["queue_strategy"] = body.queue_strategy
            if body.priority_admin is not None:
                q["priority_admin"] = body.priority_admin
            if body.priority_user is not None:
                q["priority_user"] = body.priority_user
            if body.priority_guest is not None:
                q["priority_guest"] = body.priority_guest
            system_state.config = config
            system_state.updated_at = datetime.utcnow()
            await session.commit()
            from config.settings import load_settings_from_database, get_settings
            await load_settings_from_database(get_settings())
            return QueueConfigResponse(
                queue_strategy=q.get("queue_strategy", "fifo"),
                priority_admin=int(q.get("priority_admin", 10)),
                priority_user=int(q.get("priority_user", 5)),
                priority_guest=int(q.get("priority_guest", 1)),
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/config/smtp", response_model=SMTPConfigResponse)
async def update_smtp_config(
    smtp_config: SMTPConfigRequest,
    actor_context: ActorContext = Depends(get_admin_user),
) -> SMTPConfigResponse:
    """
    Update SMTP configuration.
    
    Requires admin privileges.
    Note: Changes require service restart to take effect.
    """
    try:
        async with db_adapter.async_session() as session:
            result = await session.execute(select(SystemState).limit(1))
            system_state = result.scalar_one_or_none()
            
            if not system_state:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="System state not found"
                )
            
            # Update config
            config = system_state.config or {}
            config["smtp"] = {
                "enabled": smtp_config.enabled,
                "host": smtp_config.host,
                "port": smtp_config.port,
                "user": smtp_config.user,
                "password": smtp_config.password,  # Store in DB (should be encrypted in production)
                "use_tls": smtp_config.use_tls,
                "from_email": smtp_config.from_email,
                "from_name": smtp_config.from_name
            }
            
            system_state.config = config
            system_state.updated_at = datetime.utcnow()
            
            await session.commit()
            
            # Return masked password
            return SMTPConfigResponse(
                enabled=smtp_config.enabled,
                host=smtp_config.host,
                port=smtp_config.port,
                user=smtp_config.user,
                password="***" if smtp_config.password else "",
                use_tls=smtp_config.use_tls,
                from_email=smtp_config.from_email,
                from_name=smtp_config.from_name
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update SMTP config: {str(e)}"
        )


@router.get("/config/smtp", response_model=SMTPConfigResponse)
async def get_smtp_config(
    actor_context: ActorContext = Depends(get_admin_user),
) -> SMTPConfigResponse:
    """
    Get current SMTP configuration.
    
    Requires admin privileges.
    """
    try:
        async with db_adapter.async_session() as session:
            result = await session.execute(select(SystemState).limit(1))
            system_state = result.scalar_one_or_none()
            
            if not system_state:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="System state not found"
                )
            
            config = system_state.config or {}
            smtp_config = config.get("smtp", {})
            
            return SMTPConfigResponse(
                enabled=smtp_config.get("enabled", False),
                host=smtp_config.get("host", "smtp.gmail.com"),
                port=smtp_config.get("port", 587),
                user=smtp_config.get("user", ""),
                password="***" if smtp_config.get("password") else "",
                use_tls=smtp_config.get("use_tls", True),
                from_email=smtp_config.get("from_email", "noreply@simpleseccheck.local"),
                from_name=smtp_config.get("from_name", "SimpleSecCheck")
            )
            
    except HTTPException:
        raise
    except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get SMTP config: {str(e)}"
            )


# ============================================================================
# Audit Log Endpoints
# ============================================================================

@router.get("/audit-log")
async def get_audit_log(
    request: Request,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user_id: Optional[str] = Query(None),
    action_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    actor_context: ActorContext = Depends(get_admin_user),
) -> Dict[str, Any]:
    """
    Get audit log entries with filtering and pagination.
    
    Requires admin privileges.
    """
    try:
        # Parse dates
        start_dt = None
        end_dt = None
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        result = await AuditLogService.get_audit_log(
            limit=limit,
            offset=offset,
            user_id=user_id,
            action_type=action_type,
            start_date=start_dt,
            end_date=end_dt,
            search=search
        )
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get audit log: {str(e)}"
        )


@router.post("/audit-log/export")
async def export_audit_log(
    request: Request,
    format: str = Query("json", pattern="^(json|csv)$"),
    user_id: Optional[str] = Query(None),
    action_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    actor_context: ActorContext = Depends(get_admin_user),
):
    """
    Export audit log in specified format (JSON or CSV).
    
    Requires admin privileges.
    """
    try:
        # Parse dates
        start_dt = None
        end_dt = None
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        data = await AuditLogService.export_audit_log(
            format=format,
            user_id=user_id,
            action_type=action_type,
            start_date=start_dt,
            end_date=end_dt
        )
        
        from fastapi.responses import Response
        
        if format == "csv":
            return Response(
                content=data,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=audit_log_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"}
            )
        else:
            return Response(
                content=data,
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=audit_log_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"}
            )
    except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to export audit log: {str(e)}"
            )


# ============================================================================
# User Management Endpoints
# ============================================================================

class UserCreateRequest(BaseModel):
    """Request for creating a new user."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    role: str = Field(default="user", pattern="^(admin|user)$")


class UserUpdateRequest(BaseModel):
    """Request for updating a user."""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    role: Optional[str] = Field(None, pattern="^(admin|user)$")
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """Response for user information."""
    id: str
    email: str
    username: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: str
    last_login: Optional[str] = None


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    request: Request,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    actor_context: ActorContext = Depends(get_admin_user),
) -> List[UserResponse]:
    """
    List all users with pagination.
    
    Requires admin privileges.
    """
    try:
        from infrastructure.database.models import User
        from uuid import UUID
        
        async with db_adapter.async_session() as session:
            result = await session.execute(
                select(User)
                .order_by(User.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            users = result.scalars().all()
            
            # Log audit event
            await AuditLogService.log_event(
                user_id=actor_context.user_id,
                user_email=actor_context.email,
                action_type="USER_LIST_VIEWED",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent")
            )
            
            return [
                UserResponse(
                    id=str(user.id),
                    email=user.email,
                    username=user.username,
                    role=user.role.value,
                    is_active=user.is_active,
                    is_verified=user.is_verified,
                    created_at=user.created_at.isoformat(),
                    last_login=user.last_login.isoformat() if user.last_login else None
                )
                for user in users
            ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list users: {str(e)}"
        )


@router.post("/users", response_model=UserResponse)
async def create_user(
    request: Request,
    user_data: UserCreateRequest,
    actor_context: ActorContext = Depends(get_admin_user),
) -> UserResponse:
    """
    Create a new user.
    
    Requires admin privileges.
    """
    try:
        from infrastructure.database.models import User, UserRoleEnum
        from api.services.password_service import PasswordService
        from uuid import UUID
        
        password_service = PasswordService()
        
        async with db_adapter.async_session() as session:
            # Check if user already exists
            result = await session.execute(
                select(User).where(
                    (User.email == user_data.email) | (User.username == user_data.username)
                )
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email or username already exists"
                )
            
            # Create user
            password_hash = password_service.hash_password(user_data.password)
            role_enum = UserRoleEnum.ADMIN if user_data.role == "admin" else UserRoleEnum.USER
            
            new_user = User(
                email=user_data.email,
                username=user_data.username,
                password_hash=password_hash,
                role=role_enum,
                is_active=True,
                is_verified=False
            )
            
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            
            # Log audit event
            await AuditLogService.log_event(
                user_id=actor_context.user_id,
                user_email=actor_context.email,
                action_type="USER_CREATED",
                target=user_data.email,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent")
            )
            
            return UserResponse(
                id=str(new_user.id),
                email=new_user.email,
                username=new_user.username,
                role=new_user.role.value,
                is_active=new_user.is_active,
                is_verified=new_user.is_verified,
                created_at=new_user.created_at.isoformat(),
                last_login=None
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    request: Request,
    user_id: str,
    user_data: UserUpdateRequest,
    actor_context: ActorContext = Depends(get_admin_user),
) -> UserResponse:
    """
    Update a user.
    
    Requires admin privileges.
    """
    try:
        from infrastructure.database.models import User, UserRoleEnum
        from uuid import UUID
        
        async with db_adapter.async_session() as session:
            user_uuid = UUID(user_id)
            result = await session.execute(select(User).where(User.id == user_uuid))
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Update fields
            if user_data.email is not None:
                user.email = user_data.email
            if user_data.username is not None:
                user.username = user_data.username
            if user_data.role is not None:
                user.role = UserRoleEnum.ADMIN if user_data.role == "admin" else UserRoleEnum.USER
            if user_data.is_active is not None:
                user.is_active = user_data.is_active
            
            user.updated_at = datetime.utcnow()
            await session.commit()
            await session.refresh(user)
            
            # Log audit event
            await AuditLogService.log_event(
                user_id=actor_context.user_id,
                user_email=actor_context.email,
                action_type="USER_UPDATED",
                target=user.email,
                details={"changes": user_data.dict(exclude_unset=True)},
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent")
            )
            
            return UserResponse(
                id=str(user.id),
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
            detail=f"Failed to update user: {str(e)}"
        )


@router.delete("/users/{user_id}")
async def delete_user(
    request: Request,
    user_id: str,
    actor_context: ActorContext = Depends(get_admin_user),
) -> Dict[str, str]:
    """
    Delete a user.
    
    Requires admin privileges.
    """
    try:
        from infrastructure.database.models import User
        from uuid import UUID
        
        async with db_adapter.async_session() as session:
            user_uuid = UUID(user_id)
            result = await session.execute(select(User).where(User.id == user_uuid))
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            user_email = user.email
            
            await session.delete(user)
            await session.commit()
            
            # Log audit event
            await AuditLogService.log_event(
                user_id=actor_context.user_id,
                user_email=actor_context.email,
                action_type="USER_DELETED",
                target=user_email,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent")
            )
            
            return {"message": "User deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )


# ============================================================================
# Feature Flags Endpoints
# ============================================================================

@router.get("/feature-flags")
async def get_feature_flags(
    actor_context: ActorContext = Depends(get_admin_user),
) -> Dict[str, Any]:
    """
    Get current feature flags.
    
    Requires admin privileges.
    """
    try:
        async with db_adapter.async_session() as session:
            result = await session.execute(select(SystemState).limit(1))
            system_state = result.scalar_one_or_none()
            
            if not system_state:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="System state not found"
                )
            
            config = system_state.config or {}
            feature_flags = config.get("feature_flags", {})
            return {key: feature_flags.get(key, True) for key in ALL_SCAN_FEATURE_FLAG_KEYS}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get feature flags: {str(e)}"
        )


@router.put("/feature-flags")
async def update_feature_flags(
    request: Request,
    feature_flags: Dict[str, bool],
    actor_context: ActorContext = Depends(get_admin_user),
) -> Dict[str, Any]:
    """
    Update feature flags.
    
    Requires admin privileges.
    """
    try:
        async with db_adapter.async_session() as session:
            result = await session.execute(select(SystemState).limit(1))
            system_state = result.scalar_one_or_none()
            
            if not system_state:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="System state not found"
                )
            
            config = system_state.config or {}
            if "feature_flags" not in config:
                config["feature_flags"] = {}
            # Only accept keys from single source (ALL_SCAN_FEATURE_FLAG_KEYS)
            allowed = {k: bool(v) for k, v in feature_flags.items() if k in ALL_SCAN_FEATURE_FLAG_KEYS}
            old_flags = config["feature_flags"].copy()
            config["feature_flags"].update(allowed)
            
            system_state.config = config
            system_state.updated_at = datetime.utcnow()
            await session.commit()
            
            # Log audit event
            changes = {k: v for k, v in allowed.items() if old_flags.get(k) != v}
            await AuditLogService.log_event(
                user_id=actor_context.user_id,
                user_email=actor_context.email,
                action_type="FEATURE_FLAG_CHANGED",
                target="feature_flags",
                details={"changes": changes},
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent")
            )
            
            return {key: config["feature_flags"].get(key, True) for key in ALL_SCAN_FEATURE_FLAG_KEYS}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update feature flags: {str(e)}"
        )


# ============================================================================
# IP & Abuse Protection Endpoints
# ============================================================================

class BlockIPRequest(BaseModel):
    """Request for blocking an IP address."""
    ip_address: str = Field(..., description="IP address to block")
    reason: str = Field(default="manual", description="Reason for blocking")
    expires_at: Optional[str] = Field(None, description="Expiration date (ISO format), null for permanent")


class IPControlResponse(BaseModel):
    """Response for IP control dashboard."""
    blocked_ips: List[Dict[str, Any]]
    suspicious_activity: List[Dict[str, Any]]
    statistics: Dict[str, Any]


@router.get("/security/ip-control", response_model=IPControlResponse)
async def get_ip_control(
    actor_context: ActorContext = Depends(get_admin_user),
) -> IPControlResponse:
    """
    Get IP control dashboard data.
    
    Requires admin privileges.
    """
    try:
        from infrastructure.database.models import BlockedIP, IPActivity
        from sqlalchemy import func, and_
        from datetime import datetime, timedelta
        
        async with db_adapter.async_session() as session:
            # Get blocked IPs
            result = await session.execute(
                select(BlockedIP)
                .where(BlockedIP.is_active == True)
                .order_by(BlockedIP.blocked_at.desc())
            )
            blocked_ips = result.scalars().all()
            
            # Get suspicious activity (last 24 hours)
            since = datetime.utcnow() - timedelta(hours=24)
            activity_result = await session.execute(
                select(IPActivity)
                .where(IPActivity.created_at >= since)
                .order_by(IPActivity.count.desc())
                .limit(50)
            )
            suspicious = activity_result.scalars().all()
            
            # Get statistics
            stats_result = await session.execute(
                select(
                    func.count(BlockedIP.id).label('total_blocked'),
                    func.count(IPActivity.id).label('total_activity_24h')
                )
            )
            stats = stats_result.first()
            
            return IPControlResponse(
                blocked_ips=[
                    {
                        "id": str(ip.id),
                        "ip_address": str(ip.ip_address),
                        "reason": ip.reason,
                        "blocked_at": ip.blocked_at.isoformat(),
                        "expires_at": ip.expires_at.isoformat() if ip.expires_at else None
                    }
                    for ip in blocked_ips
                ],
                suspicious_activity=[
                    {
                        "ip_address": str(activity.ip_address),
                        "event_type": activity.event_type,
                        "count": activity.count,
                        "window_start": activity.window_start.isoformat(),
                        "metadata": activity.activity_metadata
                    }
                    for activity in suspicious
                ],
                statistics={
                    "total_blocked": stats.total_blocked or 0,
                    "total_activity_24h": stats.total_activity_24h or 0
                }
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get IP control data: {str(e)}"
        )


@router.post("/security/ip-control/block")
async def block_ip(
    request: Request,
    block_data: BlockIPRequest,
    actor_context: ActorContext = Depends(get_admin_user),
) -> Dict[str, str]:
    """
    Block an IP address.
    
    Requires admin privileges.
    """
    try:
        from infrastructure.database.models import BlockedIP
        from ipaddress import ip_address as validate_ip
        
        # Validate IP address
        try:
            validate_ip(block_data.ip_address)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid IP address"
            )
        
        expires_at = None
        if block_data.expires_at:
            expires_at = datetime.fromisoformat(block_data.expires_at.replace('Z', '+00:00'))
        
        async with db_adapter.async_session() as session:
            # Check if already blocked
            result = await session.execute(
                select(BlockedIP).where(BlockedIP.ip_address == block_data.ip_address)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update existing block
                existing.reason = block_data.reason
                existing.expires_at = expires_at
                existing.is_active = True
                existing.blocked_at = datetime.utcnow()
            else:
                # Create new block
                blocked_ip = BlockedIP(
                    ip_address=block_data.ip_address,
                    reason=block_data.reason,
                    blocked_by=UUID(actor_context.user_id) if actor_context.user_id else None,
                    expires_at=expires_at
                )
                session.add(blocked_ip)
            
            await session.commit()
            
            # Log audit event
            await AuditLogService.log_event(
                user_id=actor_context.user_id,
                user_email=actor_context.email,
                action_type="IP_BLOCKED",
                target=block_data.ip_address,
                details={"reason": block_data.reason, "expires_at": block_data.expires_at},
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent")
            )
            
            return {"message": f"IP {block_data.ip_address} blocked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to block IP: {str(e)}"
        )


@router.post("/security/ip-control/unblock")
async def unblock_ip(
    request: Request,
    ip_address: str = Query(..., description="IP address to unblock"),
    actor_context: ActorContext = Depends(get_admin_user),
) -> Dict[str, str]:
    """
    Unblock an IP address.
    
    Requires admin privileges.
    """
    try:
        from infrastructure.database.models import BlockedIP
        
        async with db_adapter.async_session() as session:
            result = await session.execute(
                select(BlockedIP).where(BlockedIP.ip_address == ip_address)
            )
            blocked_ip = result.scalar_one_or_none()
            
            if not blocked_ip:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="IP address not found in blocked list"
                )
            
            blocked_ip.is_active = False
            await session.commit()
            
            # Log audit event
            await AuditLogService.log_event(
                user_id=actor_context.user_id,
                user_email=actor_context.email,
                action_type="IP_UNBLOCKED",
                target=ip_address,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent")
            )
            
            return {"message": f"IP {ip_address} unblocked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unblock IP: {str(e)}"
        )


# ============================================================================
# Scan Engine Management Endpoints
# ============================================================================

class ScannerStatusResponse(BaseModel):
    """Response for scanner engine status."""
    workers_running: int
    queue_size: int
    active_scans: int
    average_scan_time: Optional[float] = None
    timeouts_today: int
    errors_today: int
    scans_completed_today: int
    queue_items: List[Dict[str, Any]] = []


@router.get("/scanner", response_model=ScannerStatusResponse)
async def get_scanner_status(
    actor_context: ActorContext = Depends(get_admin_user),
) -> ScannerStatusResponse:
    """
    Get scan engine status and metrics.
    
    Requires admin privileges.
    """
    try:
        from infrastructure.database.models import Scan
        from infrastructure.services.queue_service import QueueService
        from sqlalchemy import func, and_
        from datetime import datetime, timedelta
        
        async with db_adapter.async_session() as session:
            # Get queue size from Redis
            queue_service = QueueService()
            queue_size = await queue_service.get_queue_length()
            
            # Get active scans (running)
            active_result = await session.execute(
                select(func.count(Scan.id)).where(Scan.status == "running")
            )
            active_scans = active_result.scalar() or 0
            
            # Get today's statistics
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Timeouts today
            timeout_result = await session.execute(
                select(func.count(Scan.id)).where(
                    and_(
                        Scan.created_at >= today,
                        Scan.error_message.ilike("%timeout%")
                    )
                )
            )
            timeouts_today = timeout_result.scalar() or 0
            
            # Errors today
            error_result = await session.execute(
                select(func.count(Scan.id)).where(
                    and_(
                        Scan.created_at >= today,
                        Scan.status == "failed"
                    )
                )
            )
            errors_today = error_result.scalar() or 0
            
            # Completed scans today
            completed_result = await session.execute(
                select(func.count(Scan.id)).where(
                    and_(
                        Scan.created_at >= today,
                        Scan.status == "completed"
                    )
                )
            )
            scans_completed_today = completed_result.scalar() or 0
            
            # Average scan time (from completed scans today)
            avg_time_result = await session.execute(
                select(func.avg(Scan.duration)).where(
                    and_(
                        Scan.created_at >= today,
                        Scan.status == "completed",
                        Scan.duration.isnot(None)
                    )
                )
            )
            avg_scan_time = avg_time_result.scalar()
            
            # Get queue items (pending scans)
            queue_items_result = await session.execute(
                select(Scan)
                .where(Scan.status == "pending")
                .order_by(Scan.priority.desc(), Scan.created_at.asc())
                .limit(10)
            )
            queue_scans = queue_items_result.scalars().all()
            
            queue_items = [
                {
                    "scan_id": str(scan.id),
                    "name": scan.name,
                    "target": scan.target_url,
                    "created_at": scan.created_at.isoformat() if scan.created_at else None,
                    "priority": scan.priority
                }
                for scan in queue_scans
            ]
            
            # Workers running - this would typically come from worker health endpoint
            # For now, we'll estimate based on active scans
            workers_running = max(1, active_scans)  # At least 1 worker if there are active scans
            
            return ScannerStatusResponse(
                workers_running=workers_running,
                queue_size=queue_size,
                active_scans=active_scans,
                average_scan_time=float(avg_scan_time) if avg_scan_time else None,
                timeouts_today=timeouts_today,
                errors_today=errors_today,
                scans_completed_today=scans_completed_today,
                queue_items=queue_items
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scanner status: {str(e)}"
        )


@router.post("/scanner/pause")
async def pause_scanning(
    request: Request,
    actor_context: ActorContext = Depends(get_admin_user),
) -> Dict[str, str]:
    """
    Pause scanning (stop processing new scans).
    
    Requires admin privileges.
    Note: This is a placeholder - actual implementation would require worker coordination.
    """
    try:
        # Log audit event
        await AuditLogService.log_event(
            user_id=actor_context.user_id,
            user_email=actor_context.email,
            action_type="SCANNER_PAUSED",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent")
        )
        
        # TODO: Implement actual pause logic (would need worker API call)
        return {"message": "Scanning paused (placeholder - not yet implemented)"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pause scanning: {str(e)}"
        )


@router.post("/scanner/resume")
async def resume_scanning(
    request: Request,
    actor_context: ActorContext = Depends(get_admin_user),
) -> Dict[str, str]:
    """
    Resume scanning (start processing new scans).
    
    Requires admin privileges.
    Note: This is a placeholder - actual implementation would require worker coordination.
    """
    try:
        # Log audit event
        await AuditLogService.log_event(
            user_id=actor_context.user_id,
            user_email=actor_context.email,
            action_type="SCANNER_RESUMED",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent")
        )
        
        # TODO: Implement actual resume logic (would need worker API call)
        return {"message": "Scanning resumed (placeholder - not yet implemented)"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume scanning: {str(e)}"
        )


@router.get("/scanner-duration-stats")
async def get_scanner_duration_stats(
    actor_context: ActorContext = Depends(get_admin_user),
) -> Dict[str, Any]:
    """
    Get exact duration statistics per scanner/tool (admin only).
    Used for queue estimates; only real data, no fake defaults.
    """
    try:
        stats = await ScannerDurationService.get_all_stats()
        return {"scanner_duration_stats": stats}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scanner duration stats: {str(e)}"
        )
