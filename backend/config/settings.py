"""
Application Configuration Settings

This module defines all configuration settings for the refactored backend.
Settings are loaded from environment variables initially, then from database (SystemState)
after setup is completed.
"""
from typing import List
from urllib.parse import quote_plus

from pydantic import AliasChoices, Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables, then from database after setup."""

    # Connection string is only from POSTGRES_* (@computed_field). Ignore stray DATABASE_URL in env.
    model_config = SettingsConfigDict(extra="ignore", env_ignore=("DATABASE_URL",))

    # Application
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    USE_CASE: str = Field(default="solo", description="Use case: solo|network_intern|public_web|enterprise (loaded from database after setup)")
    SECRET_KEY: str = Field(description="Application secret (env SECRET_KEY, no default)")
    ALLOWED_HOSTS: List[str] = Field(default=["*"], description="Allowed host origins")
    # CORS: comma-separated origins (no * when using credentials). Set in compose via CORS_ORIGINS or APP_URL.
    CORS_ORIGINS: str = Field(
        default="http://localhost,http://localhost:80,http://127.0.0.1,http://127.0.0.1:80",
        description="Comma-separated CORS allowed origins (required when allow_credentials=True; set APP_URL on server)"
    )
    # Optional: single app URL (e.g. from compose). If set, appended to CORS_ORIGINS when not already present.
    APP_URL: str = Field(default="", description="Public app URL (e.g. https://scan.example.com); added to CORS origins when set")
    
    # Database — only POSTGRES_* (no DATABASE_URL env)
    POSTGRES_HOST: str = Field(default="postgres", description="PostgreSQL host")
    POSTGRES_PORT: str = Field(default="5432", description="PostgreSQL port")
    POSTGRES_USER: str = Field(default="ssc_user", description="PostgreSQL user")
    POSTGRES_PASSWORD: str = Field(description="PostgreSQL password (env POSTGRES_PASSWORD)")
    POSTGRES_DB: str = Field(default="simpleseccheck", description="PostgreSQL database name")
    # Internal Docker: false (avoids ~/.postgresql client cert paths). Remote/managed DB: true.
    POSTGRES_SSL: bool = Field(
        default=False,
        description="Use TLS to PostgreSQL (env POSTGRES_SSL). false = plain TCP (typical in Compose).",
    )
    DATABASE_POOL_SIZE: int = Field(default=20, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=30, description="Database max overflow connections")

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        """Built from POSTGRES_* only."""
        u = quote_plus(self.POSTGRES_USER)
        p = quote_plus(self.POSTGRES_PASSWORD)
        d = quote_plus(self.POSTGRES_DB)
        return f"postgresql://{u}:{p}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{d}"
    
    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    REDIS_POOL_SIZE: int = Field(default=10, description="Redis connection pool size")

    # SSE / realtime — single source for queue bounds (sse_manager + redis_sse_bridge)
    SSE_QUEUE_MAX_PER_CONNECTION: int = Field(
        default=200,
        ge=1,
        le=10_000,
        description="Max pending SSE envelopes per open EventSource connection",
    )
    SSE_REDIS_BRIDGE_QUEUE_MAX: int = Field(
        default=500,
        ge=16,
        le=50_000,
        description=(
            "Bounded queue between Redis scan_events pubsub and SSE delivery (backpressure). "
            "Legacy env alias: SCAN_EVENTS_BRIDGE_QUEUE_MAX."
        ),
        validation_alias=AliasChoices(
            "SSE_REDIS_BRIDGE_QUEUE_MAX",
            "SCAN_EVENTS_BRIDGE_QUEUE_MAX",
        ),
    )
    PROMETHEUS_METRICS_ENABLED: bool = Field(
        default=True,
        description="Register /metrics and Prometheus HTTP middleware (set false to reduce CPU if unused)",
    )
    SSE_REDIS_BRIDGE_ENABLED: bool = Field(
        default=True,
        description="Run Redis scan_events → SSE fan-out task (set false if realtime SSE is unused)",
    )

    # API
    API_HOST: str = Field(default="0.0.0.0", description="API host")
    API_PORT: int = Field(default=8000, description="API port")
    API_WORKERS: int = Field(default=4, description="Number of API workers")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="json", description="Log format (json or text)")
    
    # Security
    JWT_SECRET_KEY: str = Field(description="JWT secret key (set JWT_SECRET_KEY in env)")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    JWT_EXPIRATION_MINUTES: int = Field(default=1440, description="JWT token expiration in minutes")
    
    # Authentication: AUTH_MODE = how to log in; ACCESS_MODE = who may use the system
    AUTH_MODE: str = Field(default="free", description="Authentication mode (login mechanism): free|basic|jwt")
    ACCESS_MODE: str = Field(default="public", description="Who may use the system: public (all open) | mixed (public scan/queue, login for dashboard) | private (login required for all)")
    LOGIN_REQUIRED: bool = Field(default=False, description="Derived: True when ACCESS_MODE=private")
    SESSION_SECRET: str = Field(description="Session secret (env SESSION_SECRET, no default)")
    # Auth config block (registration)
    ALLOW_SELF_REGISTRATION: bool = Field(default=False, description="Allow users to self-register (sign up)")
    REGISTRATION_APPROVAL: str = Field(default="auto", description="When self-registration is on: 'auto' = new users active immediately; 'admin_approval' = new users need admin to activate")
    REQUIRE_EMAIL_VERIFICATION: bool = Field(default=False, description="When True, users must verify their email before they can log in (admin setting)")
    
    # Feature Flags (granular control, set from use case or overridden in admin).
    # Keys must match domain.services.target_permission_policy.ALL_SCAN_FEATURE_FLAG_KEYS (single source of truth).
    ALLOW_LOCAL_PATHS: bool = Field(default=True, description="Allow local file system paths as scan targets")
    # Network-related: one flag per target type (clear separation)
    ALLOW_WEBSITE_SCANS: bool = Field(default=True, description="Allow website URL scans (https://...)")
    ALLOW_API_ENDPOINT_SCANS: bool = Field(default=True, description="Allow API endpoint scans")
    ALLOW_NETWORK_HOST_SCANS: bool = Field(default=True, description="Allow network host/IP scans")
    ALLOW_KUBERNETES_CLUSTER_SCANS: bool = Field(default=True, description="Allow Kubernetes cluster scans")
    ALLOW_REMOTE_CONTAINERS: bool = Field(default=True, description="Allow remote container registry scans (Docker Hub, ghcr.io, etc.)")
    ALLOW_LOCAL_CONTAINERS: bool = Field(default=True, description="Allow scanning images from local Docker / local registry (localhost, 127.0.0.1). Admin-only when enabled.")
    ALLOW_GIT_REPOS: bool = Field(default=True, description="Allow Git repository scans")
    ALLOW_ZIP_UPLOAD: bool = Field(default=True, description="Allow ZIP file uploads as scan targets")
    # ZIP upload limits (used by upload API when implemented)
    ZIP_UPLOAD_MAX_BYTES: int = Field(default=50 * 1024 * 1024, description="Max ZIP file size in bytes (default 50 MB)")
    ZIP_UPLOAD_MAX_UNCOMPRESSED_BYTES: int = Field(default=500 * 1024 * 1024, description="Max uncompressed size when extracting (default 500 MB, prevents zip bombs)")
    ZIP_UPLOAD_MAX_FILES: int = Field(default=10000, description="Max number of files in ZIP (prevents zip bombs)")
    ZIP_UPLOAD_VIRUS_SCAN_ENABLED: bool = Field(default=True, description="If True, scan uploaded ZIP with ClamAV before accepting (ClamAV is installed in backend Docker image)")
    # Upload storage: must be same path on backend and worker (shared volume in Docker)
    UPLOAD_STORAGE_PATH: str = Field(default="/app/uploads", description="Directory for extracted ZIP uploads; worker must have same path mounted")
    # Bulk scan: default only for logged-in users; admin can override to allow guests
    BULK_SCAN_ALLOW_GUESTS: bool = Field(default=False, description="If True, guests may use bulk scan (admin override). Default: only logged-in users.")
    
    # Queue strategy: fifo | priority | round_robin (admin can change in Admin → Queue/System)
    QUEUE_STRATEGY: str = Field(default="fifo", description="Queue strategy: fifo (default), priority, round_robin")
    QUEUE_PRIORITY_ADMIN: int = Field(default=10, description="Default priority for admin scans (higher = earlier)")
    QUEUE_PRIORITY_USER: int = Field(default=5, description="Default priority for logged-in user scans")
    QUEUE_PRIORITY_GUEST: int = Field(default=1, description="Default priority for guest scans")
    # Only used when user did not check/uncheck the box (config missing or None). If user explicitly unchecks = no collection always.
    COLLECT_METADATA_DEFAULT: bool = Field(default=False, description="When True: collect metadata if user did not set the option. When False (default): collect only if user checked the box. User unchecked = never collect. Env: COLLECT_METADATA_DEFAULT=true.")
    
    # Scanner assets (DBs, manifests, etc.): global auto-update; can be extended with per-asset or health (SonarQube, Docker) in DB
    SCANNER_ASSETS_AUTO_UPDATE_ENABLED: bool = Field(default=False, description="If True, scanner assets (e.g. vuln DBs) are auto-updated; else admins trigger updates manually.")
    # External Services
    GITHUB_API_URL: str = Field(default="https://api.github.com", description="GitHub API base URL")
    GITHUB_TOKEN: str = Field(default="", description="GitHub API token")
    
    # Docker
    DOCKER_SOCKET: str = Field(default="/var/run/docker.sock", description="Docker socket path")
    DOCKER_NETWORK: str = Field(default="simpleseccheck", description="Docker network name")
    
    # Results Directory Configuration (for Worker)
    # These are set in docker-compose and passed to Worker container
    # NOTE: Logs are part of Results - Scanner creates results/{scan_id}/logs/ automatically
    RESULTS_DIR_HOST: str = Field(default="/app/results", description="Host path for results directory (from Worker's perspective)")
    RESULTS_DIR_CONTAINER: str = Field(default="/app/results", description="Container path for results (what Scanner container sees)")
    
    # SMTP / Email
    SMTP_ENABLED: bool = Field(default=False, description="Enable SMTP email sending")
    SMTP_HOST: str = Field(default="smtp.gmail.com", description="SMTP server host")
    SMTP_PORT: int = Field(default=587, description="SMTP server port")
    SMTP_USER: str = Field(default="", description="SMTP username/email")
    SMTP_PASSWORD: str = Field(default="", description="SMTP password")
    SMTP_USE_TLS: bool = Field(default=True, description="Use TLS for SMTP")
    SMTP_FROM_EMAIL: str = Field(default="noreply@simpleseccheck.local", description="From email address")
    SMTP_FROM_NAME: str = Field(default="SimpleSecCheck", description="From name")
    
    # Password Reset
    PASSWORD_RESET_TOKEN_EXPIRY_HOURS: int = Field(default=1, description="Password reset token expiry in hours")

    # Email Verification (sign-up)
    EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS: int = Field(default=24, description="Email verification token expiry in hours")

    @model_validator(mode="after")
    def set_login_required_from_access_mode(self) -> "Settings":
        """Keep LOGIN_REQUIRED in sync with ACCESS_MODE."""
        self.LOGIN_REQUIRED = self.ACCESS_MODE == "private"
        return self

def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()


async def load_settings_from_database(settings_instance: Settings) -> None:
    """
    Load settings from database (SystemState) if setup is completed.
    Overrides environment variables with database values.
    """
    try:
        from infrastructure.container import get_system_state_repository
        repo = get_system_state_repository()
        state = await repo.get_singleton()
        if state and state.config:
            config = state.config
            if "use_case" in config:
                settings_instance.USE_CASE = config["use_case"]
            if "AUTH_MODE" in config:
                settings_instance.AUTH_MODE = config["AUTH_MODE"]
            auth_cfg = config.get("auth") or {}
            if isinstance(auth_cfg, dict):
                if "access_mode" in auth_cfg:
                    settings_instance.ACCESS_MODE = auth_cfg["access_mode"]
                else:
                    settings_instance.ACCESS_MODE = "public" if (config.get("AUTH_MODE") or settings_instance.AUTH_MODE) == "free" else "private"
                if "allow_self_registration" in auth_cfg:
                    settings_instance.ALLOW_SELF_REGISTRATION = auth_cfg["allow_self_registration"]
                if "registration_approval" in auth_cfg and auth_cfg["registration_approval"] in ("auto", "admin_approval"):
                    settings_instance.REGISTRATION_APPROVAL = auth_cfg["registration_approval"]
                if "require_email_verification" in auth_cfg:
                    settings_instance.REQUIRE_EMAIL_VERIFICATION = auth_cfg["require_email_verification"]
                if "bulk_scan_allow_guests" in auth_cfg:
                    settings_instance.BULK_SCAN_ALLOW_GUESTS = auth_cfg["bulk_scan_allow_guests"]
            queue_cfg = config.get("queue") or {}
            if isinstance(queue_cfg, dict):
                if "queue_strategy" in queue_cfg and queue_cfg["queue_strategy"] in ("fifo", "priority", "round_robin"):
                    settings_instance.QUEUE_STRATEGY = queue_cfg["queue_strategy"]
                if "priority_admin" in queue_cfg:
                    settings_instance.QUEUE_PRIORITY_ADMIN = int(queue_cfg["priority_admin"])
                if "priority_user" in queue_cfg:
                    settings_instance.QUEUE_PRIORITY_USER = int(queue_cfg["priority_user"])
                if "priority_guest" in queue_cfg:
                    settings_instance.QUEUE_PRIORITY_GUEST = int(queue_cfg["priority_guest"])
            settings_instance.LOGIN_REQUIRED = settings_instance.ACCESS_MODE == "private"
            if "feature_flags" in config:
                feature_flags = config["feature_flags"]
                if isinstance(feature_flags, dict):
                    from domain.policies.target_permission_policy import ALL_SCAN_FEATURE_FLAG_KEYS
                    for key in ALL_SCAN_FEATURE_FLAG_KEYS:
                        if key in feature_flags:
                            setattr(settings_instance, key, feature_flags[key])
            scanner_cfg = config.get("scanner") or config.get("scanner_assets") or {}
            if isinstance(scanner_cfg, dict) and "auto_update_enabled" in scanner_cfg:
                settings_instance.SCANNER_ASSETS_AUTO_UPDATE_ENABLED = bool(scanner_cfg["auto_update_enabled"])
    except Exception:
        # If database is not available or setup not completed, use ENV defaults
        # This is expected during initial setup
        pass


# Global settings instance
settings = get_settings()