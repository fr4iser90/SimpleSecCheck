"""
SimpleSecCheck Backend Application Layer DTOs

This module contains Data Transfer Objects (DTOs) for the application layer.
DTOs are used to transfer data between layers without exposing domain entities directly.

DTOs provide:
- Data validation and sanitization
- Layer separation and encapsulation
- JSON serialization/deserialization
- API request/response formatting

Available DTOs:
- ScanDTO: Complete scan data transfer
- ScanSummaryDTO: Scan summary for listing
- ScanStatisticsDTO: Scan statistics and metrics
- VulnerabilityDTO: Vulnerability data transfer
- ScanResultDTO: Scan result data transfer
- ResultSummaryDTO: Result summary
- AggregatedResultDTO: Aggregated results from multiple scanners
- ScanRequestDTO: Scan creation request validation
- ScanUpdateRequestDTO: Scan update request validation
- ScanFilterDTO: Scan filtering and pagination
- ResultRequestDTO: Result processing request validation
- CancelScanRequestDTO: Scan cancellation request validation
- BatchScanRequestDTO: Batch scan request validation
"""