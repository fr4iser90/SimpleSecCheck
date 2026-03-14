"""
Execution result entity for the worker domain.

Represents the result of a job execution including findings and metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from uuid import UUID


@dataclass
class ExecutionResult:
    """Represents the result of a job execution."""
    
    job_execution_id: UUID
    scan_id: UUID
    success: bool
    error_message: Optional[str] = None
    execution_time_seconds: Optional[float] = None
    container_logs: List[str] = field(default_factory=list)
    structured_results: Dict[str, Any] = field(default_factory=dict)
    file_results: Dict[str, str] = field(default_factory=dict)  # file_path -> content
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_container_log(self, log_line: str) -> None:
        """Add a container log line."""
        self.container_logs.append(log_line)
    
    def add_structured_result(self, key: str, value: Any) -> None:
        """Add a structured result."""
        self.structured_results[key] = value
    
    def add_file_result(self, file_path: str, content: str) -> None:
        """Add a file result."""
        self.file_results[file_path] = content
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata."""
        self.metadata[key] = value
    
    def set_execution_time(self, execution_time: float) -> None:
        """Set execution time in seconds."""
        self.execution_time_seconds = execution_time
    
    @property
    def has_findings(self) -> bool:
        """Check if execution produced findings."""
        return bool(self.structured_results.get("findings") or self.file_results)
    
    @property
    def finding_count(self) -> int:
        """Get the number of findings."""
        findings = self.structured_results.get("findings", [])
        return len(findings) if isinstance(findings, list) else 0
    
    @property
    def severity_breakdown(self) -> Dict[str, int]:
        """Get severity breakdown of findings."""
        findings = self.structured_results.get("findings", [])
        if not isinstance(findings, list):
            return {}
        
        severity_counts = {}
        for finding in findings:
            severity = finding.get("severity", "unknown")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return severity_counts
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "job_execution_id": str(self.job_execution_id),
            "scan_id": str(self.scan_id),
            "success": self.success,
            "error_message": self.error_message,
            "execution_time_seconds": self.execution_time_seconds,
            "container_logs_count": len(self.container_logs),
            "structured_results": self.structured_results,
            "file_results_count": len(self.file_results),
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "has_findings": self.has_findings,
            "finding_count": self.finding_count,
            "severity_breakdown": self.severity_breakdown
        }