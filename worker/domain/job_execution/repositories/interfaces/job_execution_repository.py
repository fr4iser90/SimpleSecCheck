"""
Job execution repository interface.

Defines the contract for job execution data access operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from ...entities.job_execution import JobExecution, JobExecutionStatus, ContainerState


class JobExecutionRepository(ABC):
    """Abstract base class for job execution repository implementations."""
    
    @abstractmethod
    async def create(self, job_execution: JobExecution) -> JobExecution:
        """Create a new job execution.
        
        Args:
            job_execution: Job execution to create
            
        Returns:
            Created job execution
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, job_id: UUID) -> Optional[JobExecution]:
        """Get job execution by ID.
        
        Args:
            job_id: Job execution ID
            
        Returns:
            Job execution if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_by_scan_id(self, scan_id: UUID) -> List[JobExecution]:
        """Get job executions by scan ID.
        
        Args:
            scan_id: Scan ID
            
        Returns:
            List of job executions
        """
        pass
    
    @abstractmethod
    async def update(self, job_execution: JobExecution) -> JobExecution:
        """Update a job execution.
        
        Args:
            job_execution: Job execution to update
            
        Returns:
            Updated job execution
        """
        pass
    
    @abstractmethod
    async def delete(self, job_id: UUID) -> bool:
        """Delete a job execution.
        
        Args:
            job_id: Job execution ID
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def list_active(self) -> List[JobExecution]:
        """List all active job executions.
        
        Returns:
            List of active job executions
        """
        pass
    
    @abstractmethod
    async def list_by_status(self, status: JobExecutionStatus) -> List[JobExecution]:
        """List job executions by status.
        
        Args:
            status: Job execution status
            
        Returns:
            List of job executions
        """
        pass
    
    @abstractmethod
    async def list_by_container_state(self, state: ContainerState) -> List[JobExecution]:
        """List job executions by container state.
        
        Args:
            state: Container state
            
        Returns:
            List of job executions
        """
        pass
    
    @abstractmethod
    async def get_by_container_id(self, container_id: str) -> Optional[JobExecution]:
        """Get job execution by container ID.
        
        Args:
            container_id: Container ID
            
        Returns:
            Job execution if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def update_status(self, job_id: UUID, status: JobExecutionStatus) -> bool:
        """Update job execution status.
        
        Args:
            job_id: Job execution ID
            status: New status
            
        Returns:
            True if updated, False if not found
        """
        pass
    
    @abstractmethod
    async def update_container_state(self, job_id: UUID, state: ContainerState) -> bool:
        """Update job execution container state.
        
        Args:
            job_id: Job execution ID
            state: New container state
            
        Returns:
            True if updated, False if not found
        """
        pass
    
    @abstractmethod
    async def update_container_id(self, job_id: UUID, container_id: str) -> bool:
        """Update job execution container ID.
        
        Args:
            job_id: Job execution ID
            container_id: Container ID
            
        Returns:
            True if updated, False if not found
        """
        pass
    
    @abstractmethod
    async def add_log(self, job_id: UUID, log_line: str) -> bool:
        """Add a log line to job execution.
        
        Args:
            job_id: Job execution ID
            log_line: Log line to add
            
        Returns:
            True if updated, False if not found
        """
        pass
    
    @abstractmethod
    async def update_metadata(self, job_id: UUID, key: str, value: Any) -> bool:
        """Update job execution metadata.
        
        Args:
            job_id: Job execution ID
            key: Metadata key
            value: Metadata value
            
        Returns:
            True if updated, False if not found
        """
        pass
    
    @abstractmethod
    async def cleanup_old_executions(self, max_age_days: int = 30) -> int:
        """Clean up old job executions.
        
        Args:
            max_age_days: Maximum age in days
            
        Returns:
            Number of executions cleaned up
        """
        pass