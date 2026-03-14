"""
Application Configuration Settings

This module defines all configuration settings for the refactored backend.
Settings are loaded from environment variables with sensible defaults.
"""
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    ENVIRONMENT: str = Field(default="development", description="Application environment")
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
    
    # External Services
    GITHUB_API_URL: str = Field(default="https://api.github.com", description="GitHub API base URL")
    GITHUB_TOKEN: str = Field(default="", description="GitHub API token")
    
    # Docker
    DOCKER_SOCKET: str = Field(default="/var/run/docker.sock", description="Docker socket path")
    DOCKER_NETWORK: str = Field(default="simpleseccheck", description="Docker network name")
    
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


# Global settings instance
settings = get_settings()