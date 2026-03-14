"""
Scan Exceptions

This module defines custom exceptions for scan-related operations.
These are domain exceptions that should be caught and handled appropriately.
"""
from typing import Optional


class ScanException(Exception):
    """Base exception for scan-related errors."""
    pass


class InvalidScanConfigException(ScanException):
    """Exception raised when scan configuration is invalid."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(self.message)
    
    def __str__(self):
        if self.field:
            return f"Invalid scan configuration for field '{self.field}': {self.message}"
        return f"Invalid scan configuration: {self.message}"


class InvalidScanTargetException(ScanException):
    """Exception raised when scan target is invalid."""
    
    def __init__(self, message: str, target: Optional[str] = None):
        self.message = message
        self.target = target
        super().__init__(self.message)
    
    def __str__(self):
        if self.target:
            return f"Invalid scan target '{self.target}': {self.message}"
        return f"Invalid scan target: {self.message}"


class ScanValidationException(ScanException):
    """Exception raised when scan validation fails."""
    
    def __init__(self, message: str, validation_errors: Optional[list] = None):
        self.message = message
        self.validation_errors = validation_errors or []
        super().__init__(self.message)
    
    def __str__(self):
        if self.validation_errors:
            return f"Scan validation failed: {self.message}. Errors: {', '.join(self.validation_errors)}"
        return f"Scan validation failed: {self.message}"


class ScanNotFoundException(ScanException):
    """Exception raised when scan is not found."""
    
    def __init__(self, scan_id: str):
        self.scan_id = scan_id
        super().__init__(f"Scan with ID '{scan_id}' not found")


class ScanAlreadyExistsException(ScanException):
    """Exception raised when trying to create a duplicate scan."""
    
    def __init__(self, scan_name: str, target_url: str):
        self.scan_name = scan_name
        self.target_url = target_url
        super().__init__(f"Scan '{scan_name}' for target '{target_url}' already exists")


class ScanExecutionException(ScanException):
    """Exception raised when scan execution fails."""
    
    def __init__(self, scan_id: str, message: str, scanner_name: Optional[str] = None):
        self.scan_id = scan_id
        self.message = message
        self.scanner_name = scanner_name
        super().__init__(self.message)
    
    def __str__(self):
        if self.scanner_name:
            return f"Scan execution failed for scan '{self.scan_id}', scanner '{self.scanner_name}': {self.message}"
        return f"Scan execution failed for scan '{self.scan_id}': {self.message}"


class ScanTimeoutException(ScanException):
    """Exception raised when scan execution times out."""
    
    def __init__(self, scan_id: str, timeout: int):
        self.scan_id = scan_id
        self.timeout = timeout
        super().__init__(f"Scan '{scan_id}' timed out after {timeout} seconds")


class ScanPermissionException(ScanException):
    """Exception raised when user lacks permission for scan operation."""
    
    def __init__(self, user_id: str, operation: str, scan_id: Optional[str] = None):
        self.user_id = user_id
        self.operation = operation
        self.scan_id = scan_id
        super().__init__(self._build_message())
    
    def _build_message(self) -> str:
        if self.scan_id:
            return f"User '{self.user_id}' does not have permission to '{self.operation}' scan '{self.scan_id}'"
        return f"User '{self.user_id}' does not have permission to '{self.operation}'"


class ScanConcurrencyLimitException(ScanException):
    """Exception raised when concurrent scan limit is exceeded."""
    
    def __init__(self, user_id: str, max_concurrent: int):
        self.user_id = user_id
        self.max_concurrent = max_concurrent
        super().__init__(f"User '{self.user_id}' has exceeded maximum concurrent scans limit of {max_concurrent}")


class ScanStatusTransitionException(ScanException):
    """Exception raised when invalid scan status transition is attempted."""
    
    def __init__(self, scan_id: str, current_status: str, new_status: str):
        self.scan_id = scan_id
        self.current_status = current_status
        self.new_status = new_status
        super().__init__(
            f"Invalid status transition for scan '{self.scan_id}': "
            f"from '{self.current_status}' to '{self.new_status}'"
        )


class ScannerNotFoundException(ScanException):
    """Exception raised when requested scanner is not available."""
    
    def __init__(self, scanner_name: str):
        self.scanner_name = scanner_name
        super().__init__(f"Scanner '{scanner_name}' not found or not available")


class ScannerConfigurationException(ScanException):
    """Exception raised when scanner configuration is invalid."""
    
    def __init__(self, scanner_name: str, message: str):
        self.scanner_name = scanner_name
        self.message = message
        super().__init__(f"Scanner '{scanner_name}' configuration error: {self.message}")


class VulnerabilityProcessingException(ScanException):
    """Exception raised when vulnerability processing fails."""
    
    def __init__(self, scan_id: str, message: str, scanner_name: Optional[str] = None):
        self.scan_id = scan_id
        self.message = message
        self.scanner_name = scanner_name
        super().__init__(self._build_message())
    
    def _build_message(self) -> str:
        if self.scanner_name:
            return f"Vulnerability processing failed for scan '{self.scan_id}', scanner '{self.scanner_name}': {self.message}"
        return f"Vulnerability processing failed for scan '{self.scan_id}': {self.message}"


class ResultStorageException(ScanException):
    """Exception raised when scan result storage fails."""
    
    def __init__(self, scan_id: str, message: str):
        self.scan_id = scan_id
        self.message = message
        super().__init__(f"Failed to store results for scan '{self.scan_id}': {self.message}")


class ScanQueueException(ScanException):
    """Exception raised when scan queue operations fail."""
    
    def __init__(self, message: str, queue_name: Optional[str] = None):
        self.message = message
        self.queue_name = queue_name
        super().__init__(self._build_message())
    
    def _build_message(self) -> str:
        if self.queue_name:
            return f"Scan queue '{self.queue_name}' error: {self.message}"
        return f"Scan queue error: {self.message}"


class ScanReportGenerationException(ScanException):
    """Exception raised when scan report generation fails."""
    
    def __init__(self, scan_id: str, format: str, message: str):
        self.scan_id = scan_id
        self.format = format
        self.message = message
        super().__init__(f"Failed to generate {self.format} report for scan '{self.scan_id}': {self.message}")


class ScanImportException(ScanException):
    """Exception raised when scan import fails."""
    
    def __init__(self, source: str, message: str):
        self.source = source
        self.message = message
        super().__init__(f"Failed to import scan from '{self.source}': {self.message}")


class ScanExportException(ScanException):
    """Exception raised when scan export fails."""
    
    def __init__(self, scan_id: str, format: str, message: str):
        self.scan_id = scan_id
        self.format = format
        self.message = message
        super().__init__(f"Failed to export scan '{self.scan_id}' to {self.format}: {self.message}")


class ScanDependencyException(ScanException):
    """Exception raised when scan dependencies are missing or invalid."""
    
    def __init__(self, scan_id: str, dependency: str, message: str):
        self.scan_id = scan_id
        self.dependency = dependency
        self.message = message
        super().__init__(f"Scan '{self.scan_id}' dependency '{self.dependency}' error: {self.message}")


class ScanPolicyViolationException(ScanException):
    """Exception raised when scan violates security policies."""
    
    def __init__(self, scan_id: str, policy_name: str, message: str):
        self.scan_id = scan_id
        self.policy_name = policy_name
        self.message = message
        super().__init__(f"Scan '{self.scan_id}' violates policy '{self.policy_name}': {self.message}")


class ScanQuotaExceededException(ScanException):
    """Exception raised when user scan quota is exceeded."""
    
    def __init__(self, user_id: str, quota_type: str, limit: int, current_usage: int):
        self.user_id = user_id
        self.quota_type = quota_type
        self.limit = limit
        self.current_usage = current_usage
        super().__init__(
            f"User '{self.user_id}' has exceeded {self.quota_type} quota: "
            f"{self.current_usage}/{self.limit}"
        )


class ScanSchedulingException(ScanException):
    """Exception raised when scan scheduling fails."""
    
    def __init__(self, scan_id: str, message: str):
        self.scan_id = scan_id
        self.message = message
        super().__init__(f"Failed to schedule scan '{self.scan_id}': {self.message}")


class ScanCancellationException(ScanException):
    """Exception raised when scan cancellation fails."""
    
    def __init__(self, scan_id: str, message: str):
        self.scan_id = scan_id
        self.message = message
        super().__init__(f"Failed to cancel scan '{self.scan_id}': {self.message}")


class ScanRetryException(ScanException):
    """Exception raised when scan retry fails."""
    
    def __init__(self, scan_id: str, max_retries: int, message: str):
        self.scan_id = scan_id
        self.max_retries = max_retries
        self.message = message
        super().__init__(
            f"Scan '{self.scan_id}' exceeded maximum retries ({self.max_retries}): {self.message}"
        )