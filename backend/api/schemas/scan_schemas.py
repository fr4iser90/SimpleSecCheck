"""
Scan API Schemas

This module defines Pydantic schemas for scan-related API requests and responses.
These schemas provide validation, serialization, and OpenAPI documentation.
"""
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field
from pydantic import field_validator
from domain.entities.scan import ScanType, ScanStatus
from domain.entities.target_type import TargetType


class ScanMode(str, Enum):
    """Scan mode enumeration for API."""
    QUICK = "quick"
    FULL = "full"
    CUSTOM = "custom"


class ScanDepth(str, Enum):
    """Scan depth enumeration for API."""
    SHALLOW = "shallow"
    MEDIUM = "medium"
    DEEP = "deep"


class SeverityLevel(str, Enum):
    """Severity level enumeration for API."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    NONE = "none"


class ScanConfigSchema(BaseModel):
    """Schema for scan configuration."""
    
    scan_mode: ScanMode = Field(default=ScanMode.QUICK, description="Scan mode")
    scan_depth: ScanDepth = Field(default=ScanDepth.MEDIUM, description="Scan depth")
    timeout: int = Field(default=3600, ge=60, le=86400, description="Timeout in seconds")
    max_concurrent_scanners: int = Field(default=5, ge=1, le=20, description="Max concurrent scanners")
    
    enabled_scanners: List[str] = Field(default_factory=list, description="List of enabled scanners")
    scanner_configs: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Scanner-specific configurations")
    
    target_type: str = Field(default=TargetType.GIT_REPO.value, description="Target type")
    target_depth: int = Field(default=3, ge=1, le=10, description="Target depth")
    include_paths: List[str] = Field(default_factory=list, description="Paths to include")
    exclude_paths: List[str] = Field(default_factory=list, description="Paths to exclude")
    
    fail_on_critical: bool = Field(default=False, description="Fail on critical vulnerabilities")
    fail_on_high: bool = Field(default=False, description="Fail on high vulnerabilities")
    max_critical_vulnerabilities: int = Field(default=0, ge=0, description="Max critical vulnerabilities")
    max_high_vulnerabilities: int = Field(default=10, ge=0, description="Max high vulnerabilities")
    
    output_format: str = Field(default="json", description="Output format")
    include_raw_output: bool = Field(default=False, description="Include raw scanner output")
    compress_results: bool = Field(default=True, description="Compress results")
    
    custom_rules: List[str] = Field(default_factory=list, description="Custom security rules")
    environment_variables: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    docker_options: Dict[str, Any] = Field(default_factory=dict, description="Docker execution options")
    
    finding_policy: Optional[str] = Field(None, max_length=500, description="Relative path to finding policy file (e.g. .scanning/finding-policy.json)")
    collect_metadata: Optional[bool] = Field(None, description="Include Git info, project path, etc. in the scan report")
    git_branch: Optional[str] = Field(None, max_length=255, description="Git branch to scan")
    
    @field_validator('enabled_scanners')
    def validate_scanners(cls, v):
        """Validate scanner list (allow empty when scanners are sent as top-level 'scanners')."""
        if v is None:
            return []
        return v
    
    @field_validator('include_paths', 'exclude_paths')
    def validate_paths(cls, v):
        """Validate path lists."""
        for path in v:
            if not path or not path.strip():
                raise ValueError("Paths cannot be empty")
        return v


class VulnerabilitySchema(BaseModel):
    """Schema for vulnerability data."""
    
    id: str = Field(description="Vulnerability ID")
    title: str = Field(min_length=1, max_length=500, description="Vulnerability title")
    description: str = Field(max_length=2000, description="Vulnerability description")
    severity: SeverityLevel = Field(description="Severity level")
    
    cwe_id: Optional[str] = Field(None, description="CWE identifier")
    cve_id: Optional[str] = Field(None, description="CVE identifier")
    scanner: str = Field(description="Scanner that found this vulnerability")
    scanner_version: Optional[str] = Field(None, description="Scanner version")
    
    file_path: Optional[str] = Field(None, description="File path")
    line_number: Optional[int] = Field(None, ge=1, description="Line number")
    column_number: Optional[int] = Field(None, ge=1, description="Column number")
    function_name: Optional[str] = Field(None, description="Function name")
    class_name: Optional[str] = Field(None, description="Class name")
    
    confidence: Optional[str] = Field(None, description="Confidence level")
    cvss_score: Optional[float] = Field(None, ge=0.0, le=10.0, description="CVSS score")
    cvss_vector: Optional[str] = Field(None, description="CVSS vector")
    cvss_severity: Optional[str] = Field(None, description="CVSS severity")
    
    remediation: Optional[str] = Field(None, max_length=1000, description="Remediation advice")
    references: List[str] = Field(default_factory=list, description="Reference URLs")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ScanResultSchema(BaseModel):
    """Schema for scan result data."""
    
    scan_id: str = Field(description="Scan ID")
    scanner: str = Field(description="Scanner name")
    scanner_version: Optional[str] = Field(None, description="Scanner version")
    
    status: str = Field(description="Scan status")
    message: Optional[str] = Field(None, max_length=1000, description="Status message")
    duration: Optional[float] = Field(None, ge=0, description="Duration in seconds")
    timestamp: datetime = Field(description="Timestamp")
    
    vulnerabilities: List[VulnerabilitySchema] = Field(default_factory=list, description="List of vulnerabilities")
    
    total_vulnerabilities: int = Field(ge=0, description="Total number of vulnerabilities")
    critical_vulnerabilities: int = Field(ge=0, description="Number of critical vulnerabilities")
    high_vulnerabilities: int = Field(ge=0, description="Number of high vulnerabilities")
    medium_vulnerabilities: int = Field(ge=0, description="Number of medium vulnerabilities")
    low_vulnerabilities: int = Field(ge=0, description="Number of low vulnerabilities")
    info_vulnerabilities: int = Field(ge=0, description="Number of info vulnerabilities")
    
    raw_output: Optional[str] = Field(None, description="Raw scanner output")
    raw_output_format: Optional[str] = Field(None, description="Raw output format")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ScanRequestSchema(BaseModel):
    """Schema for scan creation requests."""
    
    name: str = Field(min_length=1, max_length=200, description="Scan name")
    description: Optional[str] = Field(None, max_length=1000, description="Scan description")
    scan_type: ScanType = Field(description="Scan type")
    target_url: str = Field(min_length=1, max_length=2000, description="Target URL")
    target_type: str = Field(default=TargetType.GIT_REPO.value, description="Target type")
    
    config: Optional[ScanConfigSchema] = Field(None, description="Scan configuration")
    scanners: List[str] = Field(min_length=1, max_length=20, description="List of scanners")
    
    project_id: Optional[str] = Field(None, description="Project ID")
    scheduled_at: Optional[datetime] = Field(None, description="Scheduled start time")
    tags: List[str] = Field(default_factory=list, max_length=10, description="Scan tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @field_validator('tags')
    def validate_tags(cls, v):
        """Validate tags."""
        for tag in v:
            if not tag or not tag.strip() or len(tag) > 50:
                raise ValueError("Tags must be 1-50 characters long")
        return v


class ScanResponseSchema(BaseModel):
    """Schema for scan response."""
    
    id: str = Field(description="Scan ID")
    name: str = Field(description="Scan name")
    description: Optional[str] = Field(description="Scan description")
    scan_type: ScanType = Field(description="Scan type")
    target_url: str = Field(description="Target URL")
    target_type: str = Field(description="Target type")
    
    user_id: Optional[str] = Field(None, description="User ID")
    project_id: Optional[str] = Field(None, description="Project ID")
    
    status: ScanStatus = Field(description="Scan status")
    created_at: datetime = Field(description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    scheduled_at: Optional[datetime] = Field(None, description="Scheduled timestamp")
    
    tags: List[str] = Field(description="Scan tags")
    total_vulnerabilities: int = Field(ge=0, description="Total vulnerabilities")
    critical_vulnerabilities: int = Field(ge=0, description="Critical vulnerabilities")
    high_vulnerabilities: int = Field(ge=0, description="High vulnerabilities")
    medium_vulnerabilities: int = Field(ge=0, description="Medium vulnerabilities")
    low_vulnerabilities: int = Field(ge=0, description="Low vulnerabilities")
    info_vulnerabilities: int = Field(ge=0, description="Info vulnerabilities")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ScanSummarySchema(BaseModel):
    """Schema for scan summary."""
    
    id: str = Field(description="Scan ID")
    name: str = Field(description="Scan name")
    scan_type: ScanType = Field(description="Scan type")
    target_url: str = Field(description="Target URL")
    target_type: str = Field(description="Target type")
    status: ScanStatus = Field(description="Scan status")
    created_at: datetime = Field(description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    total_vulnerabilities: int = Field(ge=0, description="Total vulnerabilities")
    critical_vulnerabilities: int = Field(ge=0, description="Critical vulnerabilities")
    high_vulnerabilities: int = Field(ge=0, description="High vulnerabilities")
    user_id: Optional[str] = Field(None, description="User ID")
    project_id: Optional[str] = Field(None, description="Project ID")
    tags: List[str] = Field(description="Scan tags")


class ScanUpdateSchema(BaseModel):
    """Schema for scan updates."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Scan name")
    description: Optional[str] = Field(None, max_length=1000, description="Scan description")
    status: Optional[ScanStatus] = Field(None, description="Scan status")
    config: Optional[ScanConfigSchema] = Field(None, description="Scan configuration")
    tags: Optional[List[str]] = Field(None, max_length=10, description="Scan tags")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ScanFilterSchema(BaseModel):
    """Schema for scan filtering."""
    
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    project_id: Optional[str] = Field(None, description="Filter by project ID")
    status: Optional[ScanStatus] = Field(None, description="Filter by status")
    scan_type: Optional[ScanType] = Field(None, description="Filter by scan type")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    
    limit: int = Field(default=100, ge=1, le=1000, description="Limit results")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")
    sort_by: str = Field(default="created_at", description="Sort field")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$", description="Sort order")
    
    @field_validator('sort_by')
    def validate_sort_by(cls, v):
        """Validate sort field."""
        valid_fields = ['created_at', 'started_at', 'completed_at', 'name', 'status', 'total_vulnerabilities']
        if v not in valid_fields:
            raise ValueError(f"Sort field must be one of: {', '.join(valid_fields)}")
        return v


class ScannerDurationStatSchema(BaseModel):
    """Schema for one scanner's duration stats (per-tool)."""
    scanner_name: str = Field(description="Scanner/tool name")
    avg_duration_seconds: int = Field(ge=0, description="Average duration in seconds")
    min_duration_seconds: Optional[int] = Field(None, ge=0, description="Min duration in seconds")
    max_duration_seconds: Optional[int] = Field(None, ge=0, description="Max duration in seconds")
    sample_count: int = Field(ge=0, description="Number of runs")
    last_updated: Optional[str] = Field(None, description="ISO timestamp of last update")


class ScanStatisticsSchema(BaseModel):
    """Schema for scan statistics."""
    
    total_scans: int = Field(ge=0, description="Total number of scans")
    pending_scans: int = Field(ge=0, description="Number of pending scans")
    running_scans: int = Field(ge=0, description="Number of running scans")
    completed_scans: int = Field(ge=0, description="Number of completed scans")
    failed_scans: int = Field(ge=0, description="Number of failed scans")
    cancelled_scans: int = Field(ge=0, description="Number of cancelled scans")
    
    total_vulnerabilities: int = Field(ge=0, description="Total vulnerabilities found")
    critical_vulnerabilities: int = Field(ge=0, description="Critical vulnerabilities")
    high_vulnerabilities: int = Field(ge=0, description="High vulnerabilities")
    medium_vulnerabilities: int = Field(ge=0, description="Medium vulnerabilities")
    low_vulnerabilities: int = Field(ge=0, description="Low vulnerabilities")
    info_vulnerabilities: int = Field(ge=0, description="Info vulnerabilities")
    
    repository_scans: int = Field(ge=0, description="Repository scans")
    container_scans: int = Field(ge=0, description="Container scans")
    infrastructure_scans: int = Field(ge=0, description="Infrastructure scans")
    web_application_scans: int = Field(ge=0, description="Web application scans")
    
    average_scan_duration: float = Field(ge=0, description="Average scan duration in seconds")
    longest_scan_duration: float = Field(ge=0, description="Longest scan duration in seconds")
    shortest_scan_duration: float = Field(ge=0, description="Shortest scan duration in seconds")
    scanner_duration_stats: List[ScannerDurationStatSchema] = Field(
        default_factory=list,
        description="Per-scanner duration stats (avg/min/max/sample_count)",
    )


class CancelScanSchema(BaseModel):
    """Schema for scan cancellation."""
    
    scan_id: str = Field(description="Scan ID to cancel")
    reason: Optional[str] = Field(None, max_length=500, description="Cancellation reason")
    force: bool = Field(default=False, description="Force cancellation")


class BatchScanSchema(BaseModel):
    """Schema for batch scan requests."""
    
    name: str = Field(min_length=1, max_length=200, description="Batch scan name")
    description: Optional[str] = Field(None, max_length=1000, description="Batch scan description")
    
    user_id: str = Field(description="User ID")
    project_id: Optional[str] = Field(None, description="Project ID")
    
    config: Optional[ScanConfigSchema] = Field(None, description="Scan configuration")
    scanners: List[str] = Field(min_length=1, max_length=20, description="List of scanners")
    tags: List[str] = Field(default_factory=list, max_length=10, description="Scan tags")
    
    targets: List[Dict[str, str]] = Field(min_length=1, description="List of targets")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @field_validator('targets')
    def validate_targets(cls, v):
        """Validate targets."""
        for target in v:
            if not target.get('url') or not target.get('type'):
                raise ValueError("Each target must have 'url' and 'type'")
        return v


class ScanStatusResponseSchema(BaseModel):
    """Schema for scan status response."""
    
    scan_id: str = Field(description="Scan ID")
    status: str = Field(description="Current status")
    progress: float = Field(ge=0, le=100, description="Progress percentage")
    started_at: Optional[datetime] = Field(None, description="Start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    duration: Optional[float] = Field(None, ge=0, description="Duration in seconds")
    vulnerabilities_found: int = Field(ge=0, description="Vulnerabilities found")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class AggregatedResultSchema(BaseModel):
    """Schema for aggregated scan results."""
    
    scan_id: str = Field(description="Scan ID")
    total_vulnerabilities: int = Field(ge=0, description="Total vulnerabilities")
    critical_vulnerabilities: int = Field(ge=0, description="Critical vulnerabilities")
    high_vulnerabilities: int = Field(ge=0, description="High vulnerabilities")
    medium_vulnerabilities: int = Field(ge=0, description="Medium vulnerabilities")
    low_vulnerabilities: int = Field(ge=0, description="Low vulnerabilities")
    info_vulnerabilities: int = Field(ge=0, description="Info vulnerabilities")
    
    scanner_results: List[ScanResultSchema] = Field(description="Individual scanner results")
    vulnerabilities: List[VulnerabilitySchema] = Field(description="Aggregated vulnerabilities")
    
    total_scanners: int = Field(ge=0, description="Total number of scanners")
    successful_scanners: int = Field(ge=0, description="Successful scanners")
    failed_scanners: int = Field(ge=0, description="Failed scanners")
    duration: Optional[float] = Field(None, ge=0, description="Total duration")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ReportShareLinkRequestSchema(BaseModel):
    """Request to create or refresh a token-based report share path."""

    regenerate: bool = Field(
        default=False,
        description="If true, issue a new token; previous share links stop working",
    )


class ReportShareLinkResponseSchema(BaseModel):
    """Relative path with share_token; prepend request origin for a full URL."""

    share_path: str = Field(
        ...,
        description="e.g. /api/results/{scan_id}/report?share_token=...",
    )