"""
Dependency Injection Container

This module provides a centralized container for managing dependencies
and services in the application. It uses a factory pattern to create
and inject dependencies, ensuring clean separation between FastAPI
and business logic.
"""
from typing import Optional
from dependency_injector import containers, providers

from domain.domain_services.scan_validation_service import ScanValidationService
from application.services.scan_service import ScanService
from infrastructure.repositories.scan_repository import DatabaseScanRepository
from infrastructure.services.queue_service import QueueService


class Container(containers.DeclarativeContainer):
    """Dependency injection container for the application."""
    
    # Configuration
    config = providers.Configuration()
    
    # Domain Services
    scan_validation_service = providers.Factory(
        ScanValidationService
    )
    
    # Infrastructure Services
    scan_repository = providers.Singleton(
        DatabaseScanRepository
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


# Global container instance
container = Container()


def get_scan_service() -> ScanService:
    """Get ScanService instance from container."""
    return container.scan_service()