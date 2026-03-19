"""
Setup Expiry Service

This service handles automatic setup expiration and disabling after the configured
time window. Uses SystemStateRepository (DDD).
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING

from domain.entities.system_state import SystemState, SetupStatus
from domain.datetime_serialization import isoformat_utc
from api.services.security_event_service import SecurityEventService

if TYPE_CHECKING:
    from domain.repositories.system_state_repository import SystemStateRepository


class SetupExpiryService:
    """Service for managing setup expiration and automatic disabling."""

    def __init__(
        self,
        setup_window_days: int = 7,
        check_interval_minutes: int = 60,
        system_state_repository: Optional["SystemStateRepository"] = None,
    ):
        self.setup_window_days = setup_window_days
        self.check_interval_minutes = check_interval_minutes
        self.security_logger = SecurityEventService()
        self._system_state_repository = system_state_repository
        self._running = False
        self._task = None

    def _get_repo(self):
        if self._system_state_repository is not None:
            return self._system_state_repository
        from infrastructure.container import get_system_state_repository
        return get_system_state_repository()
    
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
        """Check for and disable expired setups via SystemStateRepository."""
        try:
            repo = self._get_repo()
            state = await repo.get_singleton()
            if not state:
                return
            if state.setup_status in (SetupStatus.TOKEN_GENERATED, SetupStatus.SETUP_IN_PROGRESS) and state.setup_token_created_at:
                expiry_date = state.setup_token_created_at + timedelta(days=self.setup_window_days)
                if datetime.utcnow() > expiry_date:
                    await self._disable_expired_setup(state)
        except Exception as e:
            print(f"Error checking expired setups: {e}")

    async def _disable_expired_setup(self, state: SystemState):
        """Disable an expired setup and log the event."""
        self.security_logger.log_event("SETUP_EXPIRED", {
            "setup_status": state.setup_status.value,
            "token_created_at": isoformat_utc(state.setup_token_created_at),
            "expiry_date": isoformat_utc(
                state.setup_token_created_at + timedelta(days=self.setup_window_days)
            )
            if state.setup_token_created_at
            else None,
            "action": "setup_disabled_due_to_expiry",
        })
        state.lock_setup_permanently()
        repo = self._get_repo()
        await repo.save(state)
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
        """Extend the setup window via SystemStateRepository."""
        try:
            repo = self._get_repo()
            state = await repo.get_singleton()
            if not state:
                return False
            new_creation_time = datetime.utcnow() - timedelta(days=self.setup_window_days)
            state.setup_token_created_at = new_creation_time
            state.updated_at = datetime.utcnow()
            await repo.save(state)
            self.security_logger.log_event("SETUP_WINDOW_EXTENDED", {
                "extended_by_days": days,
                "new_expiry_date": isoformat_utc(
                    new_creation_time + timedelta(days=self.setup_window_days)
                ),
                "action": "setup_window_extended",
            })
            return True
        except Exception as e:
            print(f"Error extending setup window: {e}")
            return False
    
    async def get_setup_expiry_info(self) -> Optional[dict]:
        """Get setup expiry information via SystemStateRepository."""
        try:
            repo = self._get_repo()
            state = await repo.get_singleton()
            if not state or not state.setup_token_created_at:
                return None
            expiry_date = state.setup_token_created_at + timedelta(days=self.setup_window_days)
            time_remaining = expiry_date - datetime.utcnow()
            return {
                "setup_status": state.setup_status.value,
                "token_created_at": isoformat_utc(state.setup_token_created_at),
                "expiry_date": isoformat_utc(expiry_date),
                "time_remaining_days": max(0, time_remaining.days),
                "time_remaining_hours": max(0, time_remaining.seconds // 3600),
                "setup_window_days": self.setup_window_days,
                "is_expired": datetime.utcnow() > expiry_date,
            }
        except Exception as e:
            print(f"Error getting setup expiry info: {e}")
            return None
    
    async def reset_setup_expiry(self) -> bool:
        """Reset setup expiry via SystemStateRepository."""
        try:
            repo = self._get_repo()
            state = await repo.get_singleton()
            if not state:
                return False
            state.setup_token_created_at = datetime.utcnow()
            state.updated_at = datetime.utcnow()
            await repo.save(state)
            self.security_logger.log_event("SETUP_EXPIRY_RESET", {
                "new_expiry_date": isoformat_utc(
                    datetime.utcnow() + timedelta(days=self.setup_window_days)
                ),
                "action": "setup_expiry_reset",
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