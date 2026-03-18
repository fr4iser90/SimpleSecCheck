"""
Setup Expiry Service

This service handles automatic setup expiration and disabling after the configured
time window to prevent unauthorized setup access on deployed instances.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from infrastructure.database.models import SystemState, SetupStatusEnum
from infrastructure.database.adapter import db_adapter
from api.services.security_event_service import SecurityEventService


class SetupExpiryService:
    """Service for managing setup expiration and automatic disabling."""
    
    def __init__(self, setup_window_days: int = 7, check_interval_minutes: int = 60):
        """
        Initialize SetupExpiryService.
        
        Args:
            setup_window_days: Number of days setup remains available (default: 7)
            check_interval_minutes: How often to check for expired setups (default: 60)
        """
        self.setup_window_days = setup_window_days
        self.check_interval_minutes = check_interval_minutes
        self.security_logger = SecurityEventService()
        self._running = False
        self._task = None
    
    async def start_expiry_monitor(self):
        """
        Start the background expiry monitoring task.
        """
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._expiry_monitor_loop())
        print(f"Setup expiry monitor started. Checking every {self.check_interval_minutes} minutes.")
    
    async def stop_expiry_monitor(self):
        """
        Stop the background expiry monitoring task.
        """
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("Setup expiry monitor stopped.")
    
    async def _expiry_monitor_loop(self):
        """
        Background task to check for expired setups.
        """
        while self._running:
            try:
                await self.check_expired_setups()
                await asyncio.sleep(self.check_interval_minutes * 60)
            except Exception as e:
                print(f"Error in expiry monitor: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def check_expired_setups(self):
        """
        Check for and disable expired setups.
        """
        try:
            async with db_adapter.get_session() as session:
                # Get system state
                result = await session.execute(
                    select(SystemState).where(SystemState.id == "system_state")
                )
                system_state = result.scalar_one_or_none()
                
                if not system_state:
                    return
                
                # Check if setup is in progress and expired
                if (system_state.setup_status == SetupStatusEnum.TOKEN_GENERATED or 
                    system_state.setup_status == SetupStatusEnum.SETUP_IN_PROGRESS):
                    
                    if system_state.setup_token_created_at:
                        expiry_date = system_state.setup_token_created_at + timedelta(days=self.setup_window_days)
                        
                        if datetime.utcnow() > expiry_date:
                            await self._disable_expired_setup(session, system_state)
        
        except Exception as e:
            print(f"Error checking expired setups: {e}")
    
    async def _disable_expired_setup(self, session: AsyncSession, system_state: SystemState):
        """
        Disable an expired setup and log the event.
        
        Args:
            session: Database session
            system_state: System state to update
        """
        # Log the expiry event
        self.security_logger.log_event("SETUP_EXPIRED", {
            "setup_status": system_state.setup_status.value,
            "token_created_at": system_state.setup_token_created_at.isoformat() if system_state.setup_token_created_at else None,
            "expiry_date": (system_state.setup_token_created_at + timedelta(days=self.setup_window_days)).isoformat() if system_state.setup_token_created_at else None,
            "action": "setup_disabled_due_to_expiry"
        })
        
        # Disable the setup
        system_state.setup_status = SetupStatusEnum.LOCKED
        system_state.setup_locked = True
        system_state.updated_at = datetime.utcnow()
        
        # Clear sensitive data
        system_state.setup_token_hash = None
        system_state.setup_token_created_at = None
        
        await session.commit()
        
        print(f"Setup automatically disabled due to expiry after {self.setup_window_days} days.")
    
    async def is_setup_expired(self, system_state: SystemState) -> bool:
        """
        Check if a setup has expired.
        
        Args:
            system_state: System state to check
            
        Returns:
            True if expired, False otherwise
        """
        if not system_state.setup_token_created_at:
            return False
        
        expiry_date = system_state.setup_token_created_at + timedelta(days=self.setup_window_days)
        return datetime.utcnow() > expiry_date
    
    async def extend_setup_window(self, days: int) -> bool:
        """
        Extend the setup window by the specified number of days.
        
        Args:
            days: Number of days to extend
            
        Returns:
            True if extended successfully, False otherwise
        """
        try:
            async with db_adapter.get_session() as session:
                result = await session.execute(
                    select(SystemState).where(SystemState.id == "system_state")
                )
                system_state = result.scalar_one_or_none()
                
                if not system_state:
                    return False
                
                # Extend the window by updating the creation time
                new_creation_time = datetime.utcnow() - timedelta(days=self.setup_window_days)
                system_state.setup_token_created_at = new_creation_time
                system_state.updated_at = datetime.utcnow()
                
                await session.commit()
                
                # Log the extension
                self.security_logger.log_event("SETUP_WINDOW_EXTENDED", {
                    "extended_by_days": days,
                    "new_expiry_date": (new_creation_time + timedelta(days=self.setup_window_days)).isoformat(),
                    "action": "setup_window_extended"
                })
                
                return True
                
        except Exception as e:
            print(f"Error extending setup window: {e}")
            return False
    
    async def get_setup_expiry_info(self) -> Optional[dict]:
        """
        Get setup expiry information.
        
        Returns:
            Dictionary with expiry information or None if no setup exists
        """
        try:
            async with db_adapter.get_session() as session:
                result = await session.execute(
                    select(SystemState).where(SystemState.id == "system_state")
                )
                system_state = result.scalar_one_or_none()
                
                if not system_state or not system_state.setup_token_created_at:
                    return None
                
                expiry_date = system_state.setup_token_created_at + timedelta(days=self.setup_window_days)
                time_remaining = expiry_date - datetime.utcnow()
                
                return {
                    "setup_status": system_state.setup_status.value,
                    "token_created_at": system_state.setup_token_created_at.isoformat(),
                    "expiry_date": expiry_date.isoformat(),
                    "time_remaining_days": max(0, time_remaining.days),
                    "time_remaining_hours": max(0, time_remaining.seconds // 3600),
                    "setup_window_days": self.setup_window_days,
                    "is_expired": datetime.utcnow() > expiry_date
                }
                
        except Exception as e:
            print(f"Error getting setup expiry info: {e}")
            return None
    
    async def reset_setup_expiry(self) -> bool:
        """
        Reset setup expiry by updating the creation time to now.
        
        Returns:
            True if reset successfully, False otherwise
        """
        try:
            async with db_adapter.get_session() as session:
                result = await session.execute(
                    select(SystemState).where(SystemState.id == "system_state")
                )
                system_state = result.scalar_one_or_none()
                
                if not system_state:
                    return False
                
                # Reset the creation time to now
                system_state.setup_token_created_at = datetime.utcnow()
                system_state.updated_at = datetime.utcnow()
                
                await session.commit()
                
                # Log the reset
                self.security_logger.log_event("SETUP_EXPIRY_RESET", {
                    "new_expiry_date": (datetime.utcnow() + timedelta(days=self.setup_window_days)).isoformat(),
                    "action": "setup_expiry_reset"
                })
                
                return True
                
        except Exception as e:
            print(f"Error resetting setup expiry: {e}")
            return False
    
    def get_service_status(self) -> dict:
        """
        Get the current status of the expiry service.
        
        Returns:
            Dictionary with service status information
        """
        return {
            "running": self._running,
            "setup_window_days": self.setup_window_days,
            "check_interval_minutes": self.check_interval_minutes,
            "monitor_task_active": self._task is not None and not self._task.done()
        }