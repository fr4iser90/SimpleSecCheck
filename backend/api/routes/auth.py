"""
Authentication API Routes

This module defines the FastAPI routes for authentication operations.
Supports both JWT authentication and guest session management.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field

from api.deps.actor_context import (
    get_actor_context, get_authenticated_user, get_admin_user,
    ActorContext, ActorContextDependency
)
from config.settings import settings


class LoginRequest(BaseModel):
    """Schema for login requests."""
    
    email: EmailStr = Field(description="User email address")
    password: str = Field(min_length=8, max_length=128, description="User password")


class LoginResponse(BaseModel):
    """Schema for login responses."""
    
    access_token: str = Field(description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Token expiration in seconds")
    user_id: str = Field(description="User ID")
    email: str = Field(description="User email")
    name: Optional[str] = Field(None, description="User name")


class LogoutResponse(BaseModel):
    """Schema for logout responses."""
    
    message: str = Field(default="Successfully logged out", description="Logout message")


class PasswordResetRequest(BaseModel):
    """Schema for password reset requests."""
    
    email: EmailStr = Field(description="User email address")


class PasswordResetResponse(BaseModel):
    """Schema for password reset responses."""
    
    message: str = Field(description="Password reset message")


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""
    
    token: str = Field(description="Password reset token")
    new_password: str = Field(min_length=8, max_length=128, description="New password")


class SessionInfo(BaseModel):
    """Schema for session information."""
    
    session_id: Optional[str] = Field(None, description="Session ID")
    user_id: Optional[str] = Field(None, description="User ID")
    is_authenticated: bool = Field(description="Authentication status")
    email: Optional[str] = Field(None, description="User email")
    name: Optional[str] = Field(None, description="User name")
    expires_at: Optional[str] = Field(None, description="Session expiration time")


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["authentication"],
    responses={
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        422: {"description": "Unprocessable Entity"},
        500: {"description": "Internal Server Error"},
    },
)


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="User login",
    description="Authenticate a user with email and password, returning a JWT token.",
    response_description="JWT token and user information",
)
async def login(
    login_request: LoginRequest,
    response: Response,
    actor_context: ActorContext = Depends(get_actor_context),
    actor_context_dependency: ActorContextDependency = Depends(),
) -> LoginResponse:
    """
    User login endpoint.
    
    - **login_request**: Email and password for authentication
    - **response**: FastAPI response object for setting cookies
    - **actor_context**: Current actor context (for guest session cleanup)
    - **actor_context_dependency**: Actor context dependency for token creation
    
    Note: This is a placeholder implementation. In production, you would:
    - Validate credentials against a database
    - Hash passwords properly
    - Implement rate limiting
    - Add additional security measures
    """
    try:
        from infrastructure.database.adapter import db_adapter
        from api.services.password_service import PasswordService
        from sqlalchemy import select
        from infrastructure.database.models import User
        
        email = login_request.email
        password = login_request.password
        
        if not email or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email and password are required"
            )
        
        password_service = PasswordService()
        
        # Get user from database
        async with db_adapter.async_session() as session:
            result = await session.execute(
                select(User).where(User.email == email, User.is_active == True)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            # Verify password
            if not password_service.verify_password(password, user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            # Update last login
            from datetime import datetime
            user.last_login = datetime.utcnow()
            await session.commit()
            
            user_id = str(user.id)
            name = user.username or email.split('@')[0].title()
        
        # Create JWT token
        access_token = actor_context_dependency.create_jwt_token(
            user_id=user_id,
            email=email,
            name=name
        )
        
        # Clear any existing guest session
        if not actor_context.is_authenticated and actor_context.session_id:
            actor_context_dependency.clear_session_cookie(response)
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.jwt_expiration_minutes * 60,
            user_id=user_id,
            email=email,
            name=name,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="User logout",
    description="Logout the current user and clear authentication tokens.",
    response_description="Logout confirmation",
)
async def logout(
    response: Response,
    actor_context: ActorContext = Depends(get_actor_context),
    actor_context_dependency: ActorContextDependency = Depends(),
) -> LogoutResponse:
    """
    User logout endpoint.
    
    - **response**: FastAPI response object for clearing cookies
    - **actor_context**: Current actor context
    - **actor_context_dependency**: Actor context dependency for cookie management
    """
    try:
        # Clear session cookie
        actor_context_dependency.clear_session_cookie(response)
        
        # Note: JWT tokens are stateless, so we can't invalidate them server-side
        # The client should discard the token
        # For enhanced security, you could implement a token blacklist in Redis
        
        return LogoutResponse(
            message="Successfully logged out"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )


@router.get(
    "/session",
    response_model=SessionInfo,
    summary="Get session information",
    description="Get information about the current session (authenticated user or guest).",
    response_description="Session information",
)
async def get_session_info(
    actor_context: ActorContext = Depends(get_actor_context),
) -> SessionInfo:
    """
    Get current session information.
    
    - **actor_context**: Current actor context
    
    Returns information about the current session, whether authenticated or guest.
    """
    try:
        return SessionInfo(
            session_id=actor_context.session_id,
            user_id=actor_context.user_id,
            is_authenticated=actor_context.is_authenticated,
            email=actor_context.email,
            name=actor_context.name,
            expires_at=None,  # Would be calculated based on token/session expiration
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session info: {str(e)}"
        )


@router.post(
    "/refresh",
    response_model=LoginResponse,
    summary="Refresh authentication token",
    description="Refresh the JWT token for authenticated users.",
    response_description="New JWT token",
)
async def refresh_token(
    response: Response,
    actor_context: ActorContext = Depends(get_authenticated_user),
    actor_context_dependency: ActorContextDependency = Depends(),
) -> LoginResponse:
    """
    Refresh JWT token.
    
    - **response**: FastAPI response object
    - **actor_context**: Current authenticated user context
    - **actor_context_dependency**: Actor context dependency for token creation
    
    Note: This endpoint requires authentication.
    """
    try:
        if not actor_context.is_authenticated:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Create new JWT token
        access_token = actor_context_dependency.create_jwt_token(
            user_id=actor_context.user_id,
            email=actor_context.email,
            name=actor_context.name
        )
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.jwt_expiration_minutes * 60,
            user_id=actor_context.user_id,
            email=actor_context.email,
            name=actor_context.name,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}"
        )


@router.get(
    "/me",
    response_model=LoginResponse,
    summary="Get current user information",
    description="Get information about the currently authenticated user.",
    response_description="User information",
)
async def get_current_user(
    actor_context: ActorContext = Depends(get_authenticated_user),
) -> LoginResponse:
    """
    Get current user information.
    
    - **actor_context**: Current authenticated user context
    
    Note: This endpoint requires authentication.
    """
    try:
        if not actor_context.is_authenticated:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        return LoginResponse(
            access_token="",  # Token not included in response for security
            token_type="bearer",
            expires_in=settings.jwt_expiration_minutes * 60,
            user_id=actor_context.user_id,
            email=actor_context.email,
            name=actor_context.name,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user info: {str(e)}"
        )


@router.get(
    "/admin/users",
    response_model=SessionInfo,
    summary="Admin: List all users",
    description="List all authenticated users (admin only).",
    response_description="List of user sessions",
)
async def list_users(
    actor_context: ActorContext = Depends(get_admin_user),
) -> SessionInfo:
    """
    List all users (admin only).
    
    - **actor_context**: Current admin user context
    
    Note: This is a placeholder implementation. In production, you would:
    - Query the database for all users
    - Implement proper pagination
    - Add filtering options
    """
    try:
        # Placeholder implementation
        # In production, this would query the database for all users
        return SessionInfo(
            session_id=None,
            user_id=actor_context.user_id,
            is_authenticated=True,
            email=actor_context.email,
            name=actor_context.name,
            expires_at=None,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list users: {str(e)}"
        )


@router.post(
    "/guest",
    response_model=SessionInfo,
    summary="Create guest session",
    description="Create a new guest session for anonymous users.",
    response_description="Guest session information",
)
async def create_guest_session(
    response: Response,
    actor_context: ActorContext = Depends(get_actor_context),
    actor_context_dependency: ActorContextDependency = Depends(),
) -> SessionInfo:
    """
    Create a new guest session.
    
    - **response**: FastAPI response object for setting cookies
    - **actor_context**: Current actor context (for cleanup if needed)
    - **actor_context_dependency**: Actor context dependency for session creation
    
    This endpoint allows explicit creation of guest sessions.
    Guest sessions are automatically created when accessing other endpoints without authentication.
    """
    try:
        # If already authenticated, return current session
        if actor_context.is_authenticated:
            return SessionInfo(
                session_id=actor_context.session_id,
                user_id=actor_context.user_id,
                is_authenticated=actor_context.is_authenticated,
                email=actor_context.email,
                name=actor_context.name,
                expires_at=None,
            )
        
        # Create new guest session
        new_context = await actor_context_dependency._create_guest_session(response)
        
        return SessionInfo(
            session_id=new_context.session_id,
            user_id=new_context.user_id,
            is_authenticated=new_context.is_authenticated,
            email=new_context.email,
            name=new_context.name,
            expires_at=None,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create guest session: {str(e)}"
        )


@router.delete(
    "/session/{session_id}",
    response_model=LogoutResponse,
    summary="Admin: Delete session",
    description="Delete a specific session (admin only).",
    response_description="Session deletion confirmation",
)
async def delete_session(
    session_id: str,
    actor_context: ActorContext = Depends(get_admin_user),
    actor_context_dependency: ActorContextDependency = Depends(),
) -> LogoutResponse:
    """
    Delete a specific session (admin only).
    
    - **session_id**: ID of the session to delete
    - **actor_context**: Current admin user context
    - **actor_context_dependency**: Actor context dependency for session management
    
    Note: This is a placeholder implementation. In production, you would:
    - Remove the session from Redis/database
    - Invalidate any associated tokens
    """
    try:
        # Placeholder implementation
        # In production, this would remove the session from storage
        
        return LogoutResponse(
            message=f"Session {session_id} deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {str(e)}"
        )


@router.post(
    "/password-reset/request",
    response_model=PasswordResetResponse,
    summary="Request password reset",
    description="Request a password reset token via email.",
    response_description="Password reset request confirmation",
)
async def request_password_reset(
    reset_request: PasswordResetRequest,
) -> PasswordResetResponse:
    """
    Request password reset.
    
    - **reset_request**: Email address for password reset
    
    Always returns success (security: don't reveal if email exists).
    If email exists and SMTP is configured, sends reset email.
    """
    try:
        from infrastructure.database.adapter import db_adapter
        from api.services.password_service import PasswordService
        from api.services.email_service import EmailService
        
        password_service = PasswordService()
        email_service = EmailService()
        
        # Get user by email
        async with db_adapter.async_session() as session:
            user = await password_service.get_user_by_email(session, reset_request.email)
            
            if user:
                # Create reset token
                plain_token, token_model = await password_service.create_reset_token(
                    session, str(user.id)
                )
                
                # Send email if SMTP is enabled
                if email_service.is_enabled():
                    reset_url = email_service.get_reset_url(plain_token)
                    email_sent = await email_service.send_password_reset_email(
                        to_email=user.email,
                        reset_token=plain_token,
                        reset_url=reset_url
                    )
                    
                    if not email_sent:
                        # Log warning but don't fail the request
                        from infrastructure.logging_config import get_logger
                        logger = get_logger("api.routes.auth")
                        logger.warning("Failed to send password reset email", email=user.email)
        
        # Always return success (security: don't reveal if email exists)
        return PasswordResetResponse(
            message="If the email exists, a password reset link has been sent."
        )
        
    except Exception as e:
        from infrastructure.logging_config import get_logger
        logger = get_logger("api.routes.auth")
        logger.error("Password reset request failed", error=str(e))
        # Still return success to prevent email enumeration
        return PasswordResetResponse(
            message="If the email exists, a password reset link has been sent."
        )


@router.post(
    "/password-reset/confirm",
    response_model=PasswordResetResponse,
    summary="Confirm password reset",
    description="Reset password using reset token.",
    response_description="Password reset confirmation",
)
async def confirm_password_reset(
    reset_confirm: PasswordResetConfirm,
) -> PasswordResetResponse:
    """
    Confirm password reset.
    
    - **reset_confirm**: Reset token and new password
    
    Validates token, checks expiration, updates password, and invalidates token.
    """
    try:
        from infrastructure.database.adapter import db_adapter
        from api.services.password_service import PasswordService
        from sqlalchemy import select
        from infrastructure.database.models import User
        
        if not reset_confirm.token or len(reset_confirm.token) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )
        
        password_service = PasswordService()
        
        async with db_adapter.async_session() as session:
            # Verify token
            token_model = await password_service.verify_reset_token(
                session, reset_confirm.token
            )
            
            if not token_model:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired reset token"
                )
            
            # Get user
            result = await session.execute(
                select(User).where(User.id == token_model.user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Update password
            await password_service.update_user_password(
                session, user, reset_confirm.new_password
            )
            
            # Mark token as used
            await password_service.mark_token_used(session, token_model)
        
        return PasswordResetResponse(
            message="Password has been reset successfully. You can now login with your new password."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        from infrastructure.logging_config import get_logger
        logger = get_logger("api.routes.auth")
        logger.error("Password reset confirmation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password reset failed: {str(e)}"
        )