"""
Dependency Injection Container

This module provides a centralized container for managing dependencies
and services in the application. It uses a factory pattern to create
and inject dependencies, ensuring clean separation between FastAPI
and business logic.
"""
from typing import Optional
from dependency_injector import containers, providers

from domain.services.scan_validation_service import ScanValidationService
from application.services.scan_service import ScanService
from application.services.scan_target_service import ScanTargetService
from application.services.user_service import UserService
from application.services.api_key_service import ApiKeyService
from application.services.github_repo_service import GitHubRepoService
from application.services.setup_status_service import SetupStatusService
from infrastructure.repositories.scan_repository import DatabaseScanRepository
from infrastructure.repositories.api_key_repository import DatabaseApiKeyRepository
from infrastructure.repositories.github_repo_repository import DatabaseGitHubRepoRepository
from infrastructure.repositories.repo_scan_history_repository import DatabaseRepoScanHistoryRepository
from infrastructure.repositories.system_state_repository import DatabaseSystemStateRepository
from infrastructure.repositories.scanner_repository import DatabaseScannerRepository
from infrastructure.repositories.scanner_tool_settings_repository import DatabaseScannerToolSettingsRepository
from infrastructure.repositories.scan_target_repository import DatabaseScanTargetRepository
from infrastructure.repositories.scan_steps_repository import DatabaseScanStepsRepository
from infrastructure.repositories.user_repository import DatabaseUserRepository
from infrastructure.repositories.blocked_ip_repository import DatabaseBlockedIPRepository
from infrastructure.repositories.password_reset_token_repository import DatabasePasswordResetTokenRepository
from infrastructure.repositories.email_verification_token_repository import DatabaseEmailVerificationTokenRepository
from infrastructure.repositories.audit_log_repository import DatabaseAuditLogRepository
from infrastructure.repositories.scanner_duration_stats_repository import DatabaseScannerDurationStatsRepository
from infrastructure.services.queue_service import QueueService


class Container(containers.DeclarativeContainer):
    """Dependency injection container for the application."""
    
    # Configuration
    config = providers.Configuration()
    
    # Domain Services
    scan_validation_service = providers.Factory(
        ScanValidationService
    )
    
    # Infrastructure – Repositories
    scan_repository = providers.Singleton(
        DatabaseScanRepository
    )
    scan_target_repository = providers.Singleton(
        DatabaseScanTargetRepository
    )
    scan_steps_repository = providers.Singleton(
        DatabaseScanStepsRepository
    )
    user_repository = providers.Singleton(
        DatabaseUserRepository
    )
    api_key_repository = providers.Singleton(
        DatabaseApiKeyRepository
    )
    github_repo_repository = providers.Singleton(
        DatabaseGitHubRepoRepository
    )
    repo_scan_history_repository = providers.Singleton(
        DatabaseRepoScanHistoryRepository
    )
    system_state_repository = providers.Singleton(
        DatabaseSystemStateRepository
    )
    scanner_repository = providers.Singleton(
        DatabaseScannerRepository
    )
    scanner_tool_settings_repository = providers.Singleton(
        DatabaseScannerToolSettingsRepository
    )
    blocked_ip_repository = providers.Singleton(
        DatabaseBlockedIPRepository
    )
    audit_log_repository = providers.Singleton(
        DatabaseAuditLogRepository
    )
    password_reset_token_repository = providers.Singleton(
        DatabasePasswordResetTokenRepository
    )
    email_verification_token_repository = providers.Singleton(
        DatabaseEmailVerificationTokenRepository
    )
    scanner_duration_stats_repository = providers.Singleton(
        DatabaseScannerDurationStatsRepository
    )
    
    queue_service = providers.Singleton(
        QueueService
    )
    
    # Application Services
    scan_service = providers.Factory(
        ScanService,
        validation_service=scan_validation_service,
        scan_repository=scan_repository,
        queue_service=queue_service,
        result_service=None  # Not yet implemented
    )
    scan_target_service = providers.Factory(
        ScanTargetService,
        target_repository=scan_target_repository,
    )
    user_service = providers.Factory(
        UserService,
        user_repository=user_repository,
    )
    api_key_service = providers.Factory(
        ApiKeyService,
        api_key_repository=api_key_repository,
    )
    github_repo_service = providers.Factory(
        GitHubRepoService,
        github_repo_repository=github_repo_repository,
    )
    setup_status_service = providers.Factory(
        SetupStatusService,
        user_repository=user_repository,
        system_state_repository=system_state_repository,
    )


# Global container instance
container = Container()


def get_scan_service() -> ScanService:
    """Get ScanService instance from container."""
    return container.scan_service()


def get_scan_target_service() -> ScanTargetService:
    """Get ScanTargetService instance from container."""
    return container.scan_target_service()


def get_user_service() -> UserService:
    """Get UserService instance from container."""
    return container.user_service()


def get_api_key_service() -> ApiKeyService:
    """Get ApiKeyService instance from container."""
    return container.api_key_service()


def get_github_repo_service() -> GitHubRepoService:
    """Get GitHubRepoService instance from container."""
    return container.github_repo_service()


def get_setup_status_service() -> SetupStatusService:
    """Get SetupStatusService instance from container."""
    return container.setup_status_service()


def get_github_repo_repository():
    """Get GitHubRepoRepository instance from container."""
    return container.github_repo_repository()


def get_repo_scan_history_repository():
    """Get RepoScanHistoryRepository instance from container."""
    return container.repo_scan_history_repository()


def get_scan_repository():
    """Get ScanRepository instance from container."""
    return container.scan_repository()


def get_scan_target_repository():
    """Get ScanTargetRepository instance from container."""
    return container.scan_target_repository()


def get_scan_steps_repository():
    """Get ScanStepsRepository instance from container."""
    return container.scan_steps_repository()


def get_system_state_repository():
    """Get SystemStateRepository instance from container."""
    return container.system_state_repository()


def get_scanner_repository():
    """Get ScannerRepository instance from container."""
    return container.scanner_repository()


def get_scanner_tool_settings_repository():
    """Get ScannerToolSettingsRepository instance from container."""
    return container.scanner_tool_settings_repository()


def get_blocked_ip_repository():
    """Get BlockedIPRepository instance from container."""
    return container.blocked_ip_repository()


def get_password_reset_token_repository():
    """Get PasswordResetTokenRepository instance from container."""
    return container.password_reset_token_repository()


def get_email_verification_token_repository():
    """Get EmailVerificationTokenRepository instance from container."""
    return container.email_verification_token_repository()


def get_audit_log_repository():
    """Get AuditLogRepository instance from container."""
    return container.audit_log_repository()


def get_scanner_duration_stats_repository():
    """Get ScannerDurationStatsRepository instance from container."""
    return container.scanner_duration_stats_repository()


async def get_database_health():
    """Get database health (connection status)."""
    from infrastructure.database.adapter import db_adapter
    return await db_adapter.get_health()


async def init_database() -> None:
    """Initialize database connection (startup)."""
    from infrastructure.database.adapter import db_adapter
    await db_adapter.init_database()


async def run_database_migrations() -> None:
    """Run database migrations (Alembic upgrade head)."""
    from infrastructure.database.adapter import db_adapter
    await db_adapter.create_tables()