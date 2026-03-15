"""
Application Configuration Settings

This module defines all configuration settings for the refactored backend.
Settings are loaded from environment variables initially, then from database (SystemState)
after setup is completed.
"""
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables, then from database after setup."""
    
    # Application
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    SECURITY_MODE: str = Field(default="permissive", description="Security mode: restricted|permissive (loaded from database after setup)")
    SECRET_KEY: str = Field(default="your-secret-key-here", description="JWT secret key")
    ALLOWED_HOSTS: List[str] = Field(default=["*"], description="Allowed host origins")
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql://postgres:password@localhost:5432/simpleseccheck",
        description="PostgreSQL database connection URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=20, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=30, description="Database max overflow connections")
    
    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    REDIS_POOL_SIZE: int = Field(default=10, description="Redis connection pool size")
    
    # API
    API_HOST: str = Field(default="0.0.0.0", description="API host")
    API_PORT: int = Field(default=8000, description="API port")
    API_WORKERS: int = Field(default=4, description="Number of API workers")
    
    # Scanner Configuration
    SCANNER_TIMEOUT: int = Field(default=3600, description="Scanner timeout in seconds")
    MAX_CONCURRENT_SCANS: int = Field(default=5, description="Maximum concurrent scans")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="json", description="Log format (json or text)")
    
    # Security
    jwt_secret_key: str = Field(default="your-secret-key-here", description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    jwt_expiration_minutes: int = Field(default=1440, description="JWT token expiration in minutes")
    
    # Authentication Modes
    AUTH_MODE: str = Field(default="free", description="Authentication mode: free|basic|jwt")
    LOGIN_REQUIRED: bool = Field(default=False, description="Whether login is required")
    SESSION_SECRET: str = Field(default="your-session-secret-here", description="Session secret key")
    
    # Feature Flags (granular control, can override SECURITY_MODE defaults)
    ALLOW_LOCAL_PATHS: bool = Field(default=True, description="Allow local file system paths as scan targets")
    ALLOW_NETWORK_SCANS: bool = Field(default=True, description="Allow network/website scans")
    ALLOW_CONTAINER_REGISTRY: bool = Field(default=True, description="Allow container registry scans")
    ALLOW_GIT_REPOS: bool = Field(default=True, description="Allow Git repository scans")
    
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
    


def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()


async def load_settings_from_database(settings_instance: Settings) -> None:
    """
    Load settings from database (SystemState) if setup is completed.
    Overrides environment variables with database values.
    """
    try:
        from infrastructure.database.adapter import db_adapter
        from infrastructure.database.models import SystemState
        from sqlalchemy import select
        
        async with db_adapter.async_session() as session:
            result = await session.execute(select(SystemState).limit(1))
            system_state = result.scalar_one_or_none()
            
            if system_state and system_state.config:
                config = system_state.config
                
                # Load SECURITY_MODE and AUTH_MODE from database
                if "SECURITY_MODE" in config:
                    settings_instance.SECURITY_MODE = config["SECURITY_MODE"]
                if "AUTH_MODE" in config:
                    settings_instance.AUTH_MODE = config["AUTH_MODE"]
                
                # Load feature flags from database
                if "feature_flags" in config:
                    feature_flags = config["feature_flags"]
                    if isinstance(feature_flags, dict):
                        if "ALLOW_LOCAL_PATHS" in feature_flags:
                            settings_instance.ALLOW_LOCAL_PATHS = feature_flags["ALLOW_LOCAL_PATHS"]
                        if "ALLOW_NETWORK_SCANS" in feature_flags:
                            settings_instance.ALLOW_NETWORK_SCANS = feature_flags["ALLOW_NETWORK_SCANS"]
                        if "ALLOW_CONTAINER_REGISTRY" in feature_flags:
                            settings_instance.ALLOW_CONTAINER_REGISTRY = feature_flags["ALLOW_CONTAINER_REGISTRY"]
                        if "ALLOW_GIT_REPOS" in feature_flags:
                            settings_instance.ALLOW_GIT_REPOS = feature_flags["ALLOW_GIT_REPOS"]
                
                # Load scanner timeout and max concurrent scans if in config
                if "scanner_timeout" in config:
                    settings_instance.SCANNER_TIMEOUT = config["scanner_timeout"]
                if "max_concurrent_scans" in config:
                    settings_instance.MAX_CONCURRENT_SCANS = config["max_concurrent_scans"]
                
    except Exception as e:
        # If database is not available or setup not completed, use ENV defaults
        # This is expected during initial setup
        pass


# Global settings instance
settings = get_settings()