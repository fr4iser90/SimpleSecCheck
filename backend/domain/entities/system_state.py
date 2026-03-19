"""
SystemState Entity

This module defines the SystemState entity which tracks system initialization and setup status.
Enhanced with enterprise-grade setup security features.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from uuid import uuid4

from domain.datetime_serialization import isoformat_utc


class SetupStatus(str, Enum):
    """Setup status enumeration."""
    NOT_INITIALIZED = "not_initialized"
    TOKEN_GENERATED = "token_generated"
    SETUP_IN_PROGRESS = "setup_in_progress"
    COMPLETED = "completed"
    LOCKED = "locked"


class SystemState:
    """System state entity for tracking setup and configuration."""
    
    def __init__(self):
        self.id: str = str(uuid4())
        self.setup_status: SetupStatus = SetupStatus.NOT_INITIALIZED
        self.version: str = "1.0.0"
        self.auth_mode: str = "free"
        self.config: Dict[str, Any] = {}
        
        # Setup token management
        self.setup_token_hash: Optional[str] = None
        self.setup_token_created_at: Optional[datetime] = None
        
        # Timestamps
        self.created_at: datetime = datetime.utcnow()
        self.updated_at: datetime = datetime.utcnow()
        self.setup_completed_at: Optional[datetime] = None
        
        # System flags
        self.database_initialized: bool = False
        self.admin_user_created: bool = False
        self.system_configured: bool = False
        
        # Security tracking
        self.setup_attempts: int = 0
        self.last_setup_attempt: Optional[datetime] = None
        self.setup_locked: bool = False
    
    def start_setup(self):
        """Start the setup process."""
        self.setup_status = SetupStatus.SETUP_IN_PROGRESS
        self.updated_at = datetime.utcnow()
    
    def complete_setup(self):
        """Mark setup as completed."""
        self.setup_status = SetupStatus.COMPLETED
        self.setup_completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.setup_locked = True
    
    def lock_setup_permanently(self):
        """Lock setup permanently after completion."""
        self.setup_status = SetupStatus.LOCKED
        self.setup_locked = True
        self.updated_at = datetime.utcnow()
        # Clear sensitive data
        self.setup_token_hash = None
        self.setup_token_created_at = None
    
    def reset_setup(self):
        """Reset setup to not started (development only)."""
        self.setup_status = SetupStatus.NOT_INITIALIZED
        self.setup_completed_at = None
        self.updated_at = datetime.utcnow()
        self.database_initialized = False
        self.admin_user_created = False
        self.system_configured = False
        self.setup_attempts = 0
        self.last_setup_attempt = None
        self.setup_locked = False
        self.setup_token_hash = None
        self.setup_token_created_at = None
    
    def generate_setup_token(self, token_hash: str, created_at: datetime):
        """Generate setup token with proper TTL field."""
        self.setup_status = SetupStatus.TOKEN_GENERATED
        self.setup_token_hash = token_hash
        self.setup_token_created_at = created_at
        self.updated_at = datetime.utcnow()
    
    def invalidate_setup_token(self):
        """Invalidate setup token after successful verification."""
        self.setup_token_hash = None
        self.setup_token_created_at = None
        self.updated_at = datetime.utcnow()
    
    def increment_attempts(self):
        """Increment setup attempt counter."""
        self.setup_attempts += 1
        self.last_setup_attempt = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def mark_database_initialized(self):
        """Mark database as initialized."""
        self.database_initialized = True
        self.updated_at = datetime.utcnow()
    
    def mark_admin_user_created(self):
        """Mark admin user as created."""
        self.admin_user_created = True
        self.updated_at = datetime.utcnow()
    
    def mark_system_configured(self):
        """Mark system as configured."""
        self.system_configured = True
        self.updated_at = datetime.utcnow()
    
    def is_setup_complete(self) -> bool:
        """Check if setup is complete."""
        return (
            self.setup_status == SetupStatus.COMPLETED and
            self.database_initialized and
            self.admin_user_created and
            self.system_configured and
            self.setup_locked
        )
    
    def is_setup_required(self) -> bool:
        """Check if setup is required."""
        return not self.is_setup_complete() and not self.setup_locked
    
    def is_setup_expired(self, ttl_hours: int = 24) -> bool:
        """Check if setup token has expired."""
        if not self.setup_token_created_at:
            return True
        
        from datetime import timedelta
        expiry = self.setup_token_created_at + timedelta(hours=ttl_hours)
        return datetime.utcnow() > expiry
    
    def update_config(self, key: str, value: Any):
        """Update system configuration."""
        self.config[key] = value
        self.updated_at = datetime.utcnow()
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get system configuration value."""
        return self.config.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert system state to dictionary."""
        return {
            'id': self.id,
            'setup_status': self.setup_status.value,
            'version': self.version,
            'auth_mode': self.auth_mode,
            'config': self.config,
            'created_at': isoformat_utc(self.created_at),
            'updated_at': isoformat_utc(self.updated_at),
            'setup_completed_at': isoformat_utc(self.setup_completed_at),
            'database_initialized': self.database_initialized,
            'admin_user_created': self.admin_user_created,
            'system_configured': self.system_configured,
            'setup_attempts': self.setup_attempts,
            'last_setup_attempt': isoformat_utc(self.last_setup_attempt),
            'setup_locked': self.setup_locked,
            'setup_token_hash': self.setup_token_hash,
            'setup_token_created_at': isoformat_utc(self.setup_token_created_at),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemState':
        """Create system state from dictionary."""
        state = cls()
        state.id = data.get('id', str(uuid4()))
        state.setup_status = SetupStatus(data.get('setup_status', 'not_initialized'))
        state.version = data.get('version', '1.0.0')
        state.auth_mode = data.get('auth_mode', 'free')
        state.config = data.get('config', {})
        state.created_at = datetime.fromisoformat(data.get('created_at', datetime.utcnow().isoformat()))
        state.updated_at = datetime.fromisoformat(data.get('updated_at', datetime.utcnow().isoformat()))
        state.setup_completed_at = datetime.fromisoformat(data['setup_completed_at']) if data.get('setup_completed_at') else None
        state.database_initialized = data.get('database_initialized', False)
        state.admin_user_created = data.get('admin_user_created', False)
        state.system_configured = data.get('system_configured', False)
        state.setup_attempts = data.get('setup_attempts', 0)
        state.last_setup_attempt = datetime.fromisoformat(data['last_setup_attempt']) if data.get('last_setup_attempt') else None
        state.setup_locked = data.get('setup_locked', False)
        state.setup_token_hash = data.get('setup_token_hash')
        state.setup_token_created_at = datetime.fromisoformat(data['setup_token_created_at']) if data.get('setup_token_created_at') else None
        return state