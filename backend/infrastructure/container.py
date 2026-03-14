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


class Container(containers.DeclarativeContainer):
    """Dependency injection container for the application."""
    
    # Configuration
    config = providers.Configuration()
    
    # Domain Services
    scan_validation_service = providers.Factory(
        ScanValidationService
    )
    
    # Application Services
    scan_service = providers.Factory(
        ScanService,
        validation_service=scan_validation_service,
        scan_repository=None,  # Would be injected in real implementation
        queue_service=None,    # Would be injected in real implementation
        result_service=None    # Would be injected in real implementation
    )


# Global container instance
container = Container()


def get_scan_service() -> ScanService:
    """Get ScanService instance from container."""
    return container.scan_service()