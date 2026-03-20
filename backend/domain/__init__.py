"""
SimpleSecCheck Backend Domain Layer

This module contains the domain entities and business logic for the refactored backend.
The domain layer is pure business logic with no external dependencies.

Entities:
- Scan: Represents a security scan job
- Vulnerability: Represents a security vulnerability
- Target: Represents a scan target (repository, container, etc.)
- Scanner: Represents a security scanner
- User: Represents a system user
- SystemState: Represents system setup and configuration state

Value Objects:
- ScanConfig: Configuration for a scan
- VulnerabilitySeverity: Severity level for vulnerabilities
- TargetConfig: Configuration for a target
- ScannerConfig: Configuration for a scanner

Domain Services:
- ScanValidationService: Validates scan configurations
- ScannerSelectionService: Selects appropriate scanners
- ResultAggregationService: Aggregates scan results
- VulnerabilityAnalysisService: Analyzes vulnerabilities

Exceptions:
- ScanException: Base exception for scan operations
- InvalidScanConfigException: Invalid scan configuration
- ScanValidationException: Scan validation failed
- ScanNotFoundException: Scan not found
- ScanExecutionException: Scan execution failed
"""

# Import entities
from .entities.scan import Scan
from .entities.vulnerability import Vulnerability
from .entities.user import User, UserRole
from .entities.system_state import SystemState, SetupStatus

# Import exceptions
from .exceptions.scan_exceptions import (
    ScanException,
    InvalidScanConfigException,
    ScanValidationException,
    ScanNotFoundException,
    ScanExecutionException,
    ScanPermissionException,
    ScanQuotaExceededException,
)

# Import domain services
from .validation.scan_validation import ScanValidationService
