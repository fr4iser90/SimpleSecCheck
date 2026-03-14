"""
Production Configuration Settings

This module defines production-specific configuration settings for the
Enterprise Setup Security System with enhanced security and monitoring.
"""
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class ProductionSettings(BaseSettings):
    """Production-specific settings with enterprise security features."""
    
    # Application
    DEBUG: bool = Field(default=False, description="Disable debug mode in production")
    ENVIRONMENT: str = Field(default="production", description="Production environment")
    SECRET_KEY: str = Field(description="JWT secret key (must be 256+ bits)")
    ALLOWED_HOSTS: List[str] = Field(description="Allowed host origins for production")
    
    # Database (Production hardened)
    DATABASE_URL: str = Field(description="PostgreSQL production database URL")
    DATABASE_POOL_SIZE: int = Field(default=50, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=100, description="Database max overflow connections")
    DATABASE_SSL_MODE: str = Field(default="require", description="SSL mode for database connections")
    DATABASE_SSL_CERT: Optional[str] = Field(default=None, description="Database SSL certificate path")
    DATABASE_SSL_KEY: Optional[str] = Field(default=None, description="Database SSL key path")
    DATABASE_SSL_CA: Optional[str] = Field(default=None, description="Database SSL CA certificate path")
    
    # Redis (Production hardened)
    REDIS_URL: str = Field(description="Redis production connection URL")
    REDIS_POOL_SIZE: int = Field(default=20, description="Redis connection pool size")
    REDIS_SSL: bool = Field(default=True, description="Enable Redis SSL")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis password")
    
    # API (Production hardened)
    API_HOST: str = Field(default="0.0.0.0", description="API host")
    API_PORT: int = Field(default=8000, description="API port")
    API_WORKERS: int = Field(default=8, description="Number of API workers")
    API_TIMEOUT: int = Field(default=30, description="API timeout in seconds")
    
    # Security (Enterprise-grade)
    JWT_SECRET_KEY: str = Field(description="JWT secret key (256+ bits)")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    JWT_EXPIRATION_MINUTES: int = Field(default=60, description="JWT token expiration in minutes")
    JWT_REFRESH_EXPIRATION_DAYS: int = Field(default=7, description="JWT refresh token expiration in days")
    
    # Setup Security (Enterprise-grade)
    SETUP_TOKEN_TTL_HOURS: int = Field(default=24, description="Setup token TTL in hours")
    SETUP_WINDOW_DAYS: int = Field(default=7, description="Setup window in days")
    SETUP_CHECK_INTERVAL_MINUTES: int = Field(default=60, description="Setup check interval in minutes")
    
    # Rate Limiting (Enterprise-grade)
    RATE_LIMIT_STORAGE_URL: str = Field(description="Rate limiting storage URL")
    RATE_LIMIT_STORAGE_TYPE: str = Field(default="redis", description="Rate limiting storage type")
    RATE_LIMIT_STORAGE_SSL: bool = Field(default=True, description="Rate limiting storage SSL")
    
    # Password Policy (Enterprise-grade)
    PASSWORD_MIN_LENGTH: int = Field(default=12, description="Minimum password length")
    PASSWORD_REQUIRE_UPPERCASE: bool = Field(default=True, description="Require uppercase letters")
    PASSWORD_REQUIRE_LOWERCASE: bool = Field(default=True, description="Require lowercase letters")
    PASSWORD_REQUIRE_NUMBERS: bool = Field(default=True, description="Require numbers")
    PASSWORD_REQUIRE_SYMBOLS: bool = Field(default=True, description="Require symbols")
    PASSWORD_MEMORY_COST: int = Field(default=65536, description="Argon2 memory cost (64MB)")
    PASSWORD_TIME_COST: int = Field(default=3, description="Argon2 time cost")
    PASSWORD_PARALLELISM: int = Field(default=4, description="Argon2 parallelism")
    
    # Logging (SIEM Integration)
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="json", description="Log format (json for SIEM)")
    LOG_STRUCTURED: bool = Field(default=True, description="Enable structured logging")
    LOG_SIEM_ENDPOINT: Optional[str] = Field(default=None, description="SIEM endpoint URL")
    LOG_SIEM_API_KEY: Optional[str] = Field(default=None, description="SIEM API key")
    LOG_RETENTION_DAYS: int = Field(default=365, description="Log retention period in days")
    
    # Monitoring (Enterprise-grade)
    METRICS_ENABLED: bool = Field(default=True, description="Enable metrics collection")
    METRICS_ENDPOINT: str = Field(default="/metrics", description="Metrics endpoint")
    HEALTH_CHECK_ENABLED: bool = Field(default=True, description="Enable health checks")
    HEALTH_CHECK_PATH: str = Field(default="/health", description="Health check path")
    
    # Security Headers (Enterprise-grade)
    SECURITY_HEADERS_ENABLED: bool = Field(default=True, description="Enable security headers")
    CORS_ALLOW_ORIGINS: List[str] = Field(description="CORS allowed origins")
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, description="CORS allow credentials")
    CORS_ALLOW_METHODS: List[str] = Field(default=["GET", "POST", "PUT", "DELETE"], description="CORS allowed methods")
    CORS_ALLOW_HEADERS: List[str] = Field(default=["*"], description="CORS allowed headers")
    
    # Session Management (Enterprise-grade)
    SESSION_TIMEOUT_MINUTES: int = Field(default=30, description="Session timeout in minutes")
    SESSION_COOKIE_SECURE: bool = Field(default=True, description="Secure session cookies")
    SESSION_COOKIE_HTTPONLY: bool = Field(default=True, description="HTTP-only session cookies")
    SESSION_COOKIE_SAMESITE: str = Field(default="Strict", description="Session cookie SameSite policy")
    
    # IP Whitelisting (Enterprise-grade)
    IP_WHITELIST_ENABLED: bool = Field(default=False, description="Enable IP whitelisting")
    IP_WHITELIST: List[str] = Field(default=[], description="Allowed IP addresses/CIDR blocks")
    TRUSTED_PROXIES: List[str] = Field(default=[], description="Trusted proxy IP addresses/CIDR blocks")
    
    # Audit Trail (Enterprise-grade)
    AUDIT_ENABLED: bool = Field(default=True, description="Enable audit trail")
    AUDIT_STORAGE_URL: str = Field(description="Audit trail storage URL")
    AUDIT_STORAGE_TYPE: str = Field(default="database", description="Audit trail storage type")
    AUDIT_RETENTION_DAYS: int = Field(default=2555, description="Audit trail retention (7 years)")
    
    # Backup and Recovery (Enterprise-grade)
    BACKUP_ENABLED: bool = Field(default=True, description="Enable automated backups")
    BACKUP_SCHEDULE: str = Field(default="0 2 * * *", description="Backup schedule (cron format)")
    BACKUP_RETENTION_DAYS: int = Field(default=30, description="Backup retention period")
    BACKUP_STORAGE_URL: str = Field(description="Backup storage URL")
    
    # External Services (Enterprise-grade)
    GITHUB_API_URL: str = Field(default="https://api.github.com", description="GitHub API base URL")
    GITHUB_TOKEN: Optional[str] = Field(default=None, description="GitHub API token")
    GITHUB_ORG_WHITELIST: List[str] = Field(default=[], description="Whitelisted GitHub organizations")
    
    # Docker (Production hardened)
    DOCKER_NETWORK: str = Field(default="simpleseccheck-prod", description="Docker network name")
    DOCKER_PRIVILEGED: bool = Field(default=False, description="Run containers in privileged mode")
    DOCKER_SECURITY_OPTIONS: List[str] = Field(default=["no-new-privileges"], description="Docker security options")
    
    # Compliance (Enterprise-grade)
    GDPR_COMPLIANCE: bool = Field(default=True, description="Enable GDPR compliance features")
    SOX_COMPLIANCE: bool = Field(default=True, description="Enable SOX compliance features")
    HIPAA_COMPLIANCE: bool = Field(default=False, description="Enable HIPAA compliance features")
    
    @validator('SECRET_KEY', 'JWT_SECRET_KEY')
    def validate_secret_key_length(cls, v):
        """Validate that secret keys are at least 256 bits (32 bytes)."""
        if v and len(v.encode()) < 32:
            raise ValueError('Secret key must be at least 256 bits (32 characters)')
        return v
    
    @validator('ALLOWED_HOSTS', 'CORS_ALLOW_ORIGINS', 'IP_WHITELIST', 'TRUSTED_PROXIES')
    def validate_host_lists(cls, v):
        """Validate host lists are not empty in production."""
        if not v:
            raise ValueError('Host lists cannot be empty in production')
        return v
    
    class Config:
        env_file = ".env.production"
        env_file_encoding = "utf-8"
        case_sensitive = True


def get_production_settings() -> ProductionSettings:
    """Get production settings instance."""
    return ProductionSettings()


# Global production settings instance
production_settings = get_production_settings()