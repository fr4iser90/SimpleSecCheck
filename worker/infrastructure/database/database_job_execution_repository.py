"""
Database implementation of the JobExecutionRepository interface.

Provides database-backed persistence for job executions.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID
from dataclasses import asdict
from contextlib import asynccontextmanager

from sqlalchemy import (
    text, select, update, delete, func, and_, or_, desc, asc,
    String, Integer, Float, Boolean, DateTime, JSON, Text
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from worker.domain.job_execution.entities.job_execution import JobExecution, JobExecutionStatus, ContainerState
from worker.domain.job_execution.repositories.interfaces.job_execution_repository import JobExecutionRepository
from worker.infrastructure.database_adapter import DatabaseAdapter


class DatabaseJobExecutionRepository(JobExecutionRepository):
    """Database implementation of the JobExecutionRepository interface."""
    
    def __init__(self, database_adapter: DatabaseAdapter):
        """Initialize the database job execution repository.
        
        Args:
            database_adapter: Database adapter instance
        """
        self.db_adapter = database_adapter
        self.logger = logging.getLogger(__name__)
    
    async def create(self, job_execution: JobExecution) -> JobExecution:
        """Create a new job execution."""
        try:
            async with self.db_adapter.get_session() as session:
                # Convert JobExecution to dict
                job_dict = asdict(job_execution)
                job_dict['id'] = str(job_execution.id)
                job_dict['scan_id'] = str(job_execution.scan_id)
                job_dict['status'] = job_execution.status.value
                job_dict['container_state'] = job_execution.container_state.value
                job_dict['started_at'] = job_execution.started_at
                job_dict['completed_at'] = job_execution.completed_at
                
                # Convert lists and dicts to JSON strings
                job_dict['execution_metadata'] = json.dumps(job_execution.execution_metadata)
                job_dict['logs'] = json.dumps(job_execution.logs)
                
                # Insert into database
                query = text("""
                    INSERT INTO job_executions (
                        id, scan_id, job_type, status, container_state,
                        container_id, started_at, completed_at, error_message,
                        execution_metadata, logs, created_at, updated_at
                    ) VALUES (
                        :id, :scan_id, :job_type, :status, :container_state,
                        :container_id, :started_at, :completed_at, :error_message,
                        :execution_metadata, :logs, :created_at, :updated_at
                    )
                    RETURNING *
                """)
                
                job_dict['created_at'] = datetime.utcnow()
                job_dict['updated_at'] = datetime.utcnow()
                
                result = await session.execute(query, job_dict)
                row = result.fetchone()
                await session.commit()
                
                return self._row_to_job_execution(row)
                
        except SQLAlchemyError as e:
            self.logger.error(f"Error creating job execution: {e}")
            raise
    
    async def get_by_id(self, job_id: UUID) -> Optional[JobExecution]:
        """Get job execution by ID."""
        try:
            async with self.db_adapter.get_session() as session:
                query = text("SELECT * FROM job_executions WHERE id = :job_id")
                result = await session.execute(query, {"job_id": str(job_id)})
                row = result.fetchone()
                
                return self._row_to_job_execution(row) if row else None
                
        except SQLAlchemyError as e:
            self.logger.error(f"Error getting job execution {job_id}: {e}")
            raise
    
    async def get_by_scan_id(self, scan_id: UUID) -> List[JobExecution]:
        """Get job executions by scan ID."""
        try:
            async with self.db_adapter.get_session() as session:
                query = text("SELECT * FROM job_executions WHERE scan_id = :scan_id ORDER BY created_at DESC")
                result = await session.execute(query, {"scan_id": str(scan_id)})
                rows = result.fetchall()
                
                return [self._row_to_job_execution(row) for row in rows]
                
        except SQLAlchemyError as e:
            self.logger.error(f"Error getting job executions for scan {scan_id}: {e}")
            raise
    
    async def update(self, job_execution: JobExecution) -> JobExecution:
        """Update a job execution."""
        try:
            async with self.db_adapter.get_session() as session:
                # Build update dict
                update_dict = {
                    'job_type': job_execution.job_type,
                    'status': job_execution.status.value,
                    'container_state': job_execution.container_state.value,
                    'container_id': job_execution.container_id,
                    'started_at': job_execution.started_at,
                    'completed_at': job_execution.completed_at,
                    'error_message': job_execution.error_message,
                    'execution_metadata': json.dumps(job_execution.execution_metadata),
                    'logs': json.dumps(job_execution.logs),
                    'updated_at': datetime.utcnow()
                }
                
                query = text("""
                    UPDATE job_executions 
                    SET job_type = :job_type, status = :status, container_state = :container_state,
                        container_id = :container_id, started_at = :started_at, completed_at = :completed_at,
                        error_message = :error_message, execution_metadata = :execution_metadata,
                        logs = :logs, updated_at = :updated_at
                    WHERE id = :job_id
                    RETURNING *
                """)
                
                update_dict['job_id'] = str(job_execution.id)
                result = await session.execute(query, update_dict)
                row = result.fetchone()
                await session.commit()
                
                return self._row_to_job_execution(row) if row else None
                
        except SQLAlchemyError as e:
            self.logger.error(f"Error updating job execution {job_execution.id}: {e}")
            raise
    
    async def delete(self, job_id: UUID) -> bool:
        """Delete a job execution."""
        try:
            async with self.db_adapter.get_session() as session:
                query = text("DELETE FROM job_executions WHERE id = :job_id")
                result = await session.execute(query, {"job_id": str(job_id)})
                await session.commit()
                
                return result.rowcount > 0
                
        except SQLAlchemyError as e:
            self.logger.error(f"Error deleting job execution {job_id}: {e}")
            raise
    
    async def list_active(self) -> List[JobExecution]:
        """List all active job executions."""
        try:
            async with self.db_adapter.get_session() as session:
                query = text("""
                    SELECT * FROM job_executions 
                    WHERE status IN ('pending', 'running') 
                    ORDER BY created_at DESC
                """)
                result = await session.execute(query)
                rows = result.fetchall()
                
                return [self._row_to_job_execution(row) for row in rows]
                
        except SQLAlchemyError as e:
            self.logger.error(f"Error listing active job executions: {e}")
            raise
    
    async def list_by_status(self, status: JobExecutionStatus) -> List[JobExecution]:
        """List job executions by status."""
        try:
            async with self.db_adapter.get_session() as session:
                query = text("SELECT * FROM job_executions WHERE status = :status ORDER BY created_at DESC")
                result = await session.execute(query, {"status": status.value})
                rows = result.fetchall()
                
                return [self._row_to_job_execution(row) for row in rows]
                
        except SQLAlchemyError as e:
            self.logger.error(f"Error listing job executions by status {status}: {e}")
            raise
    
    async def list_by_container_state(self, state: ContainerState) -> List[JobExecution]:
        """List job executions by container state."""
        try:
            async with self.db_adapter.get_session() as session:
                query = text("SELECT * FROM job_executions WHERE container_state = :state ORDER BY created_at DESC")
                result = await session.execute(query, {"state": state.value})
                rows = result.fetchall()
                
                return [self._row_to_job_execution(row) for row in rows]
                
        except SQLAlchemyError as e:
            self.logger.error(f"Error listing job executions by container state {state}: {e}")
            raise
    
    async def get_by_container_id(self, container_id: str) -> Optional[JobExecution]:
        """Get job execution by container ID."""
        try:
            async with self.db_adapter.get_session() as session:
                query = text("SELECT * FROM job_executions WHERE container_id = :container_id")
                result = await session.execute(query, {"container_id": container_id})
                row = result.fetchone()
                
                return self._row_to_job_execution(row) if row else None
                
        except SQLAlchemyError as e:
            self.logger.error(f"Error getting job execution by container ID {container_id}: {e}")
            raise
    
    async def update_status(self, job_id: UUID, status: JobExecutionStatus) -> bool:
        """Update job execution status."""
        try:
            async with self.db_adapter.get_session() as session:
                query = text("UPDATE job_executions SET status = :status, updated_at = :updated_at WHERE id = :job_id")
                result = await session.execute(query, {
                    "job_id": str(job_id),
                    "status": status.value,
                    "updated_at": datetime.utcnow()
                })
                await session.commit()
                
                return result.rowcount > 0
                
        except SQLAlchemyError as e:
            self.logger.error(f"Error updating job execution status for {job_id}: {e}")
            raise
    
    async def update_container_state(self, job_id: UUID, state: ContainerState) -> bool:
        """Update job execution container state."""
        try:
            async with self.db_adapter.get_session() as session:
                query = text("UPDATE job_executions SET container_state = :state, updated_at = :updated_at WHERE id = :job_id")
                result = await session.execute(query, {
                    "job_id": str(job_id),
                    "state": state.value,
                    "updated_at": datetime.utcnow()
                })
                await session.commit()
                
                return result.rowcount > 0
                
        except SQLAlchemyError as e:
            self.logger.error(f"Error updating job execution container state for {job_id}: {e}")
            raise
    
    async def update_container_id(self, job_id: UUID, container_id: str) -> bool:
        """Update job execution container ID."""
        try:
            async with self.db_adapter.get_session() as session:
                query = text("UPDATE job_executions SET container_id = :container_id, updated_at = :updated_at WHERE id = :job_id")
                result = await session.execute(query, {
                    "job_id": str(job_id),
                    "container_id": container_id,
                    "updated_at": datetime.utcnow()
                })
                await session.commit()
                
                return result.rowcount > 0
                
        except SQLAlchemyError as e:
            self.logger.error(f"Error updating job execution container ID for {job_id}: {e}")
            raise
    
    async def add_log(self, job_id: UUID, log_line: str) -> bool:
        """Add a log line to job execution."""
        try:
            async with self.db_adapter.get_session() as session:
                # Get current logs
                query = text("SELECT logs FROM job_executions WHERE id = :job_id")
                result = await session.execute(query, {"job_id": str(job_id)})
                row = result.fetchone()
                
                if not row:
                    return False
                
                current_logs = json.loads(row.logs) if row.logs else []
                current_logs.append(log_line)
                
                # Update logs
                query = text("UPDATE job_executions SET logs = :logs, updated_at = :updated_at WHERE id = :job_id")
                result = await session.execute(query, {
                    "job_id": str(job_id),
                    "logs": json.dumps(current_logs),
                    "updated_at": datetime.utcnow()
                })
                await session.commit()
                
                return result.rowcount > 0
                
        except SQLAlchemyError as e:
            self.logger.error(f"Error adding log to job execution {job_id}: {e}")
            raise
    
    async def update_metadata(self, job_id: UUID, key: str, value: Any) -> bool:
        """Update job execution metadata."""
        try:
            async with self.db_adapter.get_session() as session:
                # Get current metadata
                query = text("SELECT execution_metadata FROM job_executions WHERE id = :job_id")
                result = await session.execute(query, {"job_id": str(job_id)})
                row = result.fetchone()
                
                if not row:
                    return False
                
                current_metadata = json.loads(row.execution_metadata) if row.execution_metadata else {}
                current_metadata[key] = value
                
                # Update metadata
                query = text("UPDATE job_executions SET execution_metadata = :metadata, updated_at = :updated_at WHERE id = :job_id")
                result = await session.execute(query, {
                    "job_id": str(job_id),
                    "metadata": json.dumps(current_metadata),
                    "updated_at": datetime.utcnow()
                })
                await session.commit()
                
                return result.rowcount > 0
                
        except SQLAlchemyError as e:
            self.logger.error(f"Error updating metadata for job execution {job_id}: {e}")
            raise
    
    async def cleanup_old_executions(self, max_age_days: int = 30) -> int:
        """Clean up old job executions."""
        try:
            async with self.db_adapter.get_session() as session:
                cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
                
                query = text("DELETE FROM job_executions WHERE created_at < :cutoff_date")
                result = await session.execute(query, {"cutoff_date": cutoff_date})
                await session.commit()
                
                return result.rowcount
                
        except SQLAlchemyError as e:
            self.logger.error(f"Error cleaning up old job executions: {e}")
            raise
    
    def _row_to_job_execution(self, row) -> Optional[JobExecution]:
        """Convert database row to JobExecution object."""
        if not row:
            return None
        
        return JobExecution(
            id=UUID(row.id),
            scan_id=UUID(row.scan_id),
            job_type=row.job_type,
            status=JobExecutionStatus(row.status),
            container_state=ContainerState(row.container_state),
            container_id=row.container_id,
            started_at=row.started_at,
            completed_at=row.completed_at,
            error_message=row.error_message,
            execution_metadata=json.loads(row.execution_metadata) if row.execution_metadata else {},
            logs=json.loads(row.logs) if row.logs else [],
            created_at=row.created_at,
            updated_at=row.updated_at
        )