"""
User Entity

This module defines the User entity which represents a system user.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import uuid4
import hashlib


class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


@dataclass
class User:
    """System user entity."""
    
    id: str = field(default_factory=lambda: str(uuid4()))
    username: str = ""
    email: str = ""
    password_hash: str = ""
    role: UserRole = UserRole.USER
    is_active: bool = True
    is_verified: bool = False
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def set_password(self, password: str):
        """Set user password with hashing."""
        # In production, use a proper password hashing library like bcrypt
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()
        self.updated_at = datetime.utcnow()
    
    def check_password(self, password: str) -> bool:
        """Check if password matches hash."""
        # In production, use proper password verification
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()
    
    def activate(self):
        """Activate user account."""
        self.is_active = True
        self.updated_at = datetime.utcnow()
    
    def deactivate(self):
        """Deactivate user account."""
        self.is_active = False
        self.updated_at = datetime.utcnow()
    
    def verify(self):
        """Verify user account."""
        self.is_verified = True
        self.updated_at = datetime.utcnow()
    
    def promote_to_admin(self):
        """Promote user to admin."""
        self.role = UserRole.ADMIN
        self.updated_at = datetime.utcnow()
    
    def demote_to_user(self):
        """Demote user to regular user."""
        self.role = UserRole.USER
        self.updated_at = datetime.utcnow()
    
    def update_metadata(self, key: str, value: Any):
        """Update user metadata."""
        self.metadata[key] = value
        self.updated_at = datetime.utcnow()
    
    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.role == UserRole.ADMIN
    
    def is_guest(self) -> bool:
        """Check if user is guest."""
        return self.role == UserRole.GUEST
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role.value,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create user from dictionary."""
        user = cls(
            id=data.get('id', str(uuid4())),
            username=data.get('username', ''),
            email=data.get('email', ''),
            password_hash=data.get('password_hash', ''),
            role=UserRole(data.get('role', 'user')),
            is_active=data.get('is_active', True),
            is_verified=data.get('is_verified', False),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.utcnow().isoformat())),
            updated_at=datetime.fromisoformat(data.get('updated_at', datetime.utcnow().isoformat())),
            last_login=datetime.fromisoformat(data['last_login']) if data.get('last_login') else None,
            metadata=data.get('metadata', {}),
        )
        return user