"""
Test container for providing mock dependencies during testing.
"""
from unittest.mock import Mock, AsyncMock
from dependency_injector import containers, providers

from domain.services.scan_validation_service import ScanValidationService
from application.services.scan_service import ScanService
from application.dtos.scan_dto import ScanDTO
from application.dtos.request_dto import ScanFilterDTO


class _TestDependencyContainer(containers.DeclarativeContainer):
    """Test container with mock dependencies."""
    
    # Mock dependencies
    mock_scan_repository = providers.Factory(Mock)
    mock_queue_service = providers.Factory(Mock)
    mock_result_service = providers.Factory(Mock)
    
    # Domain Services
    scan_validation_service = providers.Factory(
        ScanValidationService
    )
    
    # Application Services with mock dependencies
    scan_service = providers.Factory(
        ScanService,
        validation_service=scan_validation_service,
        scan_repository=mock_scan_repository,
        queue_service=mock_queue_service,
        result_service=mock_result_service
    )


# Global test container instance
test_container = _TestDependencyContainer()


def get_test_scan_service():
    """Get test ScanService instance with mock dependencies."""
    # Create a mock service with proper async methods
    mock_service = Mock()
    
    # Set up async mock methods
    mock_service.create_scan = AsyncMock(return_value=None)
    mock_service.list_scans = AsyncMock(return_value=[])
    mock_service.get_scan_by_id = AsyncMock(return_value=None)
    mock_service.update_scan = AsyncMock(return_value=None)
    mock_service.delete_scan = AsyncMock(return_value=True)
    mock_service.get_scan_status = AsyncMock(return_value={})
    mock_service.cancel_scan = AsyncMock(return_value=None)
    mock_service.retry_scan = AsyncMock(return_value=None)
    mock_service.get_scan_statistics = AsyncMock(return_value=None)
    mock_service.get_recent_scans = AsyncMock(return_value=[])
    
    return mock_service
