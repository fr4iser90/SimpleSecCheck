"""
Admin API Routes

Handles admin-only operations like system configuration updates.
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from api.deps.actor_context import get_admin_user, ActorContext
from infrastructure.database.adapter import db_adapter
from infrastructure.database.models import SystemState
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
