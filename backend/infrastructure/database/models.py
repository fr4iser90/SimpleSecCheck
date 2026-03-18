"""
Database Models

This module defines the SQLAlchemy models for the refactored backend.
Models represent the database schema and provide ORM functionality.
"""
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, JSON, Enum as SQLEnum, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID, INET
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
    scheduled_at = Column(DateTime, nullable=True)  # Scheduled start time (optional)
    
    # Results
    results = Column(JSON, default=list)
    total_vulnerabilities = Column(Integer, default=0, nullable=False)
    critical_vulnerabilities = Column(Integer, default=0, nullable=False)
    high_vulnerabilities = Column(Integer, default=0, nullable=False)
    medium_vulnerabilities = Column(Integer, default=0, nullable=False)
    low_vulnerabilities = Column(Integer, default=0, nullable=False)
    info_vulnerabilities = Column(Integer, default=0, nullable=False)
    duration = Column(Integer, nullable=True)  # Duration in seconds
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Metadata
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    project_id = Column(String(255), nullable=True)
    tags = Column(JSON, default=list)
    scan_metadata = Column(JSON, default=dict)  # Additional metadata (e.g. session_id for guest sessions)
    
    # Queue priority (higher = earlier in queue)
    priority = Column(Integer, default=0, nullable=False, index=True)
    
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
    scanner_metadata = Column(JSON, default=dict, nullable=False)  # description, categories, icon, assets (renamed from 'metadata' - SQLAlchemy reserved)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_discovered_at = Column(DateTime, nullable=True)  # When scanner was last discovered from container
    
    def __repr__(self):
        return f"<Scanner(id={self.id}, name='{self.name}', scan_types={self.scan_types}, enabled={self.enabled})>"


class ScannerToolSettings(Base):
    """
    Admin overrides. PK scanner_key = tools_key slug (semgrep, sonarqube), not display name.
    """
    __tablename__ = "scanner_tool_settings"

    scanner_key = Column(String(128), primary_key=True, nullable=False)  # tools_key
    enabled = Column(Boolean, nullable=True)  # NULL = use scanners.enabled from discovery
    timeout_seconds = Column(Integer, nullable=True)  # NULL = use execution.timeout from scanner metadata
    config = Column(JSON, default=dict, nullable=False)  # e.g. SONAR_HOST_URL, SONAR_TOKEN, SNYK_TOKEN
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    def __repr__(self):
        return f"<ScannerToolSettings(scanner_key={self.scanner_key})>"


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


# ============================================================================
# Admin & Security Models
# ============================================================================

class AuditLog(Base):
    """Audit log database model for tracking all security-relevant events."""
    
    __tablename__ = "audit_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    user_email = Column(String(255), nullable=True)  # Denormalized for deleted users
    action_type = Column(String(50), nullable=False, index=True)  # USER_CREATED, FEATURE_FLAG_CHANGED, etc.
    target = Column(String(500), nullable=True)  # What was changed
    details = Column(JSON, default=dict)  # Additional context
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    result = Column(String(20), default="success", nullable=False)  # success, failure
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action_type='{self.action_type}', user_id={self.user_id})>"


class BlockedIP(Base):
    """Blocked IP addresses for abuse protection."""
    
    __tablename__ = "blocked_ips"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ip_address = Column(INET, nullable=False, unique=True, index=True)
    reason = Column(String(100), nullable=True)  # brute_force, request_spike, manual, etc.
    blocked_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    blocked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # NULL = permanent
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Relationships
    blocker = relationship("User", foreign_keys=[blocked_by])
    
    def __repr__(self):
        return f"<BlockedIP(id={self.id}, ip_address='{self.ip_address}', reason='{self.reason}')>"


class IPActivity(Base):
    """IP activity tracking for abuse detection."""
    
    __tablename__ = "ip_activity"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ip_address = Column(INET, nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # login_failed, request_spike, etc.
    count = Column(Integer, default=1, nullable=False)
    window_start = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    window_end = Column(DateTime, nullable=True)
    activity_metadata = Column(JSON, default=dict)  # Renamed from 'metadata' (SQLAlchemy reserved)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<IPActivity(id={self.id}, ip_address='{self.ip_address}', event_type='{self.event_type}', count={self.count})>"


class VulnerabilityRule(Base):
    """Vulnerability rules database model."""
    
    __tablename__ = "vulnerability_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(String(100), unique=True, nullable=False, index=True)  # e.g., "hardcoded-secrets"
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(20), nullable=False)  # critical, high, medium, low
    category = Column(String(50), nullable=True)  # secrets, dependency, sast, etc.
    enabled = Column(Boolean, default=True, nullable=False)
    custom = Column(Boolean, default=False, nullable=False)  # Custom rule vs. built-in
    config = Column(JSON, default=dict)  # Rule-specific configuration
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<VulnerabilityRule(id={self.id}, rule_id='{self.rule_id}', name='{self.name}', enabled={self.enabled})>"


class SuppressionRule(Base):
    """Suppression rules for ignoring specific findings."""
    
    __tablename__ = "suppression_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(String(100), ForeignKey("vulnerability_rules.rule_id"), nullable=True)
    pattern = Column(String(500), nullable=True)  # Path pattern or vulnerability ID
    reason = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    expires_at = Column(DateTime, nullable=True)  # NULL = never expires
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    rule = relationship("VulnerabilityRule", foreign_keys=[rule_id])
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<SuppressionRule(id={self.id}, pattern='{self.pattern}', is_active={self.is_active})>"


class ScanPolicy(Base):
    """Scan policies/templates database model."""
    
    __tablename__ = "scan_policies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    enabled_scanners = Column(ARRAY(String), default=list, nullable=False)  # ['secrets', 'dependency', 'sast']
    scan_depth = Column(String(20), default="medium", nullable=False)  # quick, medium, deep
    timeout = Column(Integer, default=3600, nullable=False)
    severity_threshold = Column(String(20), nullable=True)  # Only report findings >= this severity
    custom_rules = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<ScanPolicy(id={self.id}, name='{self.name}', is_default={self.is_default})>"


class NotificationChannel(Base):
    """Notification channels database model."""
    
    __tablename__ = "notification_channels"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_type = Column(String(50), nullable=False)  # email, slack, discord, webhook
    name = Column(String(255), nullable=False)
    config = Column(JSON, nullable=False)  # Channel-specific config (webhook URL, etc.)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<NotificationChannel(id={self.id}, channel_type='{self.channel_type}', name='{self.name}')>"


class NotificationRule(Base):
    """Notification rules database model."""
    
    __tablename__ = "notification_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(50), nullable=False)  # scan_completed, critical_vuln, etc.
    channel_id = Column(UUID(as_uuid=True), ForeignKey("notification_channels.id"), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    severity_filter = Column(ARRAY(String), default=list)  # Only notify for these severities
    rate_limit = Column(Integer, nullable=True)  # Max notifications per hour
    template = Column(Text, nullable=True)  # Custom notification template
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    channel = relationship("NotificationChannel", foreign_keys=[channel_id])
    
    def __repr__(self):
        return f"<NotificationRule(id={self.id}, event_type='{self.event_type}', channel_id={self.channel_id})>"


# ============================================================================
# User Features Models
# ============================================================================

class UserGitHubRepo(Base):
    """User GitHub repositories database model."""
    
    __tablename__ = "user_github_repos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    repo_url = Column(String(500), nullable=False)
    repo_owner = Column(String(255), nullable=True)  # GitHub username/organization (e.g. "fr4iser90")
    repo_name = Column(String(255), nullable=False)  # Repository name only (e.g. "my-repo"), NOT "owner/repo"
    branch = Column(String(100), default="main", nullable=False)
    auto_scan_enabled = Column(Boolean, default=True, nullable=False)
    scan_on_push = Column(Boolean, default=True, nullable=False)
    scan_frequency = Column(String(20), default="on_push", nullable=False)  # on_push, daily, weekly, manual
    scanners = Column(JSON, default=list, nullable=True)  # List of scanner names for this repo (if None, uses all code scanners)
    github_token = Column(Text, nullable=True)  # Encrypted GitHub token
    webhook_secret = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<UserGitHubRepo(id={self.id}, repo_url='{self.repo_url}', user_id={self.user_id})>"


class RepoScanHistory(Base):
    """Repository scan history database model."""
    
    __tablename__ = "repo_scan_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_id = Column(UUID(as_uuid=True), ForeignKey("user_github_repos.id"), nullable=False, index=True)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=True)
    branch = Column(String(100), nullable=True)
    commit_hash = Column(String(100), nullable=True)
    score = Column(Integer, nullable=True)  # 0-100
    vulnerabilities = Column(JSON, default=dict)  # {critical: 0, high: 2, medium: 5, low: 10}
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    repo = relationship("UserGitHubRepo", foreign_keys=[repo_id])
    scan = relationship("Scan", foreign_keys=[scan_id])
    
    def __repr__(self):
        return f"<RepoScanHistory(id={self.id}, repo_id={self.repo_id}, score={self.score})>"


class ScannerDurationStats(Base):
    """Scanner duration statistics for estimating scan times."""
    
    __tablename__ = "scanner_duration_stats"
    
    scanner_name = Column(String(100), primary_key=True, nullable=False)
    avg_duration_seconds = Column(Integer, nullable=False, default=120)  # Default: 2 minutes
    min_duration_seconds = Column(Integer, nullable=True)
    max_duration_seconds = Column(Integer, nullable=True)
    sample_count = Column(Integer, nullable=False, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<ScannerDurationStats(scanner_name='{self.scanner_name}', avg_duration={self.avg_duration_seconds}s, samples={self.sample_count})>"


class APIKey(Base):
    """API keys database model."""
    
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)  # Hashed API key
    name = Column(String(255), nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # NULL = never expires
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<APIKey(id={self.id}, name='{self.name}', user_id={self.user_id})>"


# Additional indexes for new tables
Index('idx_audit_log_user_id', AuditLog.user_id)
Index('idx_audit_log_action_type', AuditLog.action_type)
Index('idx_audit_log_created_at', AuditLog.created_at)
Index('idx_blocked_ips_ip_address', BlockedIP.ip_address)
Index('idx_blocked_ips_is_active', BlockedIP.is_active)
Index('idx_ip_activity_ip_address', IPActivity.ip_address)
Index('idx_ip_activity_event_type', IPActivity.event_type)
Index('idx_ip_activity_window', IPActivity.window_start, IPActivity.window_end)
Index('idx_user_github_repos_user_id', UserGitHubRepo.user_id)
Index('idx_repo_scan_history_repo_id', RepoScanHistory.repo_id)
Index('idx_repo_scan_history_created_at', RepoScanHistory.created_at)
Index('idx_scanner_duration_stats_scanner_name', ScannerDurationStats.scanner_name)
Index('idx_api_keys_user_id', APIKey.user_id)
Index('idx_api_keys_key_hash', APIKey.key_hash)