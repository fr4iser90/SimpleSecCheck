"""
Job execution entity for the worker domain.

Represents a scan job execution with container specifications and execution state.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID


class JobExecutionStatus(Enum):
    """Status of a job execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ContainerState(Enum):
    """State of a container."""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    RESTARTING = "restarting"
    REMOVING = "removing"
    EXITED = "exited"
    DEAD = "dead"


@dataclass
class JobExecution:
    """Represents a scan job execution."""
    
    id: UUID
    scan_id: UUID
    job_type: str
    container_spec: 'ContainerSpec'
    status: JobExecutionStatus = JobExecutionStatus.PENDING
    container_state: ContainerState = ContainerState.CREATED
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    container_id: Optional[str] = None
    execution_metadata: Dict[str, Any] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)
    
    def start_execution(self) -> None:
        """Mark job as started."""
        self.status = JobExecutionStatus.RUNNING
        self.container_state = ContainerState.RUNNING
        self.started_at = datetime.utcnow()
    
    def complete_execution(self, success: bool = True, error_message: Optional[str] = None) -> None:
        """Mark job as completed."""
        self.status = JobExecutionStatus.COMPLETED if success else JobExecutionStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        self.container_state = ContainerState.EXITED
    
    def cancel_execution(self) -> None:
        """Mark job as cancelled."""
        self.status = JobExecutionStatus.CANCELLED
        self.completed_at = datetime.utcnow()
        self.container_state = ContainerState.EXITED
    
    def add_log(self, log_line: str) -> None:
        """Add a log line to the execution."""
        self.logs.append(f"{datetime.utcnow().isoformat()}: {log_line}")
    
    def update_metadata(self, key: str, value: Any) -> None:
        """Update execution metadata."""
        self.execution_metadata[key] = value
    
    @property
    def execution_time_seconds(self) -> Optional[float]:
        """Get execution time in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def is_running(self) -> bool:
        """Check if job is currently running."""
        return self.status == JobExecutionStatus.RUNNING
    
    @property
    def is_completed(self) -> bool:
        """Check if job is completed (success or failure)."""
        return self.status in [JobExecutionStatus.COMPLETED, JobExecutionStatus.FAILED, JobExecutionStatus.CANCELLED]