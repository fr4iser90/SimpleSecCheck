"""
Database Models

This module defines the SQLAlchemy models for the refactored backend.
Models represent the database schema and provide ORM functionality.
"""
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, JSON, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from enum import Enum

from domain.entities.user import UserRole
from domain.entities.system_state import SetupStatus

Base = declarative_base()


class UserRoleEnum(str, Enum):
    """SQLAlchemy enum for user roles."""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class SetupStatusEnum(str, Enum):
    """SQLAlchemy enum for setup status."""
    NOT_INITIALIZED = "not_initialized"
    TOKEN_GENERATED = "token_generated"
    SETUP_IN_PROGRESS = "setup_in_progress"
    COMPLETED = "completed"
    LOCKED = "locked"


class User(Base):
    """User database model."""
    
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRoleEnum), default=UserRoleEnum.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    # Metadata
    user_metadata = Column(JSON, default=dict)
    
    # Relationships
    scans = relationship("Scan", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}', role='{self.role}')>"


class PasswordResetToken(Base):
    """Password reset token database model."""
    
    __tablename__ = "password_reset_tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<PasswordResetToken(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})>"


class SystemState(Base):
    """System state database model."""
    
    __tablename__ = "system_state"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    setup_status = Column(SQLEnum(SetupStatusEnum), default=SetupStatusEnum.NOT_INITIALIZED, nullable=False)
    version = Column(String(20), default="1.0.0", nullable=False)
    auth_mode = Column(String(20), default="free", nullable=False)
    
    # Setup token management
    setup_token_hash = Column(String(255), nullable=True)
    setup_token_created_at = Column(DateTime, nullable=True)
    
    # Configuration
    config = Column(JSON, default=dict)
    
    # SMTP Configuration (stored in config JSON, but accessible via properties)
    # config structure: {"smtp": {"enabled": bool, "host": str, "port": int, ...}}
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    setup_completed_at = Column(DateTime, nullable=True)
    
    # System flags
    database_initialized = Column(Boolean, default=False, nullable=False)
    admin_user_created = Column(Boolean, default=False, nullable=False)
    system_configured = Column(Boolean, default=False, nullable=False)
    
    # Security tracking
    setup_attempts = Column(Integer, default=0, nullable=False)
    last_setup_attempt = Column(DateTime, nullable=True)
    setup_locked = Column(Boolean, default=False, nullable=False)
    
    def __repr__(self):
        return f"<SystemState(id={self.id}, setup_status='{self.setup_status}', version='{self.version}')>"


class Scan(Base):
    """Scan database model."""
    
    __tablename__ = "scans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    scan_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    target_url = Column(String(500), nullable=False)
    target_type = Column(String(50), nullable=False)
    
    # Configuration
    scanners = Column(JSON, default=list)
    config = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Results
    results = Column(JSON, default=list)
    vulnerabilities_count = Column(Integer, default=0, nullable=False)
    duration = Column(Integer, nullable=True)  # Duration in seconds
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Metadata
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    project_id = Column(String(255), nullable=True)
    tags = Column(JSON, default=list)
    scan_metadata = Column(JSON, default=dict)  # Additional metadata (e.g. session_id for guest sessions)
    
    # Relationships
    user = relationship("User", back_populates="scans", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<Scan(id={self.id}, name='{self.name}', status='{self.status}', target='{self.target_url}')>"


class Vulnerability(Base):
    """Vulnerability database model."""
    
    __tablename__ = "vulnerabilities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Vulnerability details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False)
    cwe_id = Column(String(20), nullable=True)
    cvss_score = Column(String(10), nullable=True)
    
    # Location
    file_path = Column(String(500), nullable=True)
    line_number = Column(Integer, nullable=True)
    column_number = Column(Integer, nullable=True)
    
    # Additional info
    scanner = Column(String(100), nullable=False)
    confidence = Column(String(20), nullable=True)
    remediation = Column(Text, nullable=True)
    
    # Metadata
    vuln_metadata = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<Vulnerability(id={self.id}, title='{self.title}', severity='{self.severity}', scanner='{self.scanner}')>"


class Scanner(Base):
    """Scanner database model."""
    
    __tablename__ = "scanners"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    scan_types = Column(JSON, default=list, nullable=False)  # List of scan types: ["code", "image", etc.]
    priority = Column(Integer, default=0, nullable=False)
    requires_condition = Column(String(100), nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_discovered_at = Column(DateTime, nullable=True)  # When scanner was last discovered from container
    
    def __repr__(self):
        return f"<Scanner(id={self.id}, name='{self.name}', scan_types={self.scan_types}, enabled={self.enabled})>"


# Create indexes for better performance
from sqlalchemy import Index

# Indexes for scans
Index('idx_scans_user_id', Scan.user_id)
Index('idx_scans_status', Scan.status)
Index('idx_scans_created_at', Scan.created_at)
Index('idx_scans_target_url', Scan.target_url)

# Indexes for vulnerabilities
Index('idx_vulnerabilities_scan_id', Vulnerability.scan_id)
Index('idx_vulnerabilities_severity', Vulnerability.severity)
Index('idx_vulnerabilities_scanner', Vulnerability.scanner)

# Indexes for users
Index('idx_users_email', User.email)
Index('idx_users_username', User.username)
Index('idx_users_role', User.role)

# Indexes for scanners
Index('idx_scanners_name', Scanner.name)
Index('idx_scanners_enabled', Scanner.enabled)