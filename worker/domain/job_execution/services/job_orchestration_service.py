"""
Job orchestration service for the worker domain.

Handles the orchestration of job execution including queuing, scheduling, and coordination.
"""

import asyncio
import json
import logging
import os
import uuid
from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime, timedelta
from uuid import UUID

from worker.domain.job_execution.entities.job_execution import JobExecution, JobExecutionStatus, ContainerState
from worker.infrastructure.docker.docker_job_executor import DockerJobExecutor
from worker.domain.job_execution.services.result_processing_service import ResultProcessingService
from worker.infrastructure.queue_adapter import QueueAdapter
from worker.infrastructure.database_adapter import PostgreSQLAdapter


class JobOrchestrationService:
    """Service for orchestrating job executions."""
    
    def __init__(
        self,
        docker_job_executor: DockerJobExecutor,
        result_processing_service: ResultProcessingService,
        queue_adapter: QueueAdapter,
        database_adapter: PostgreSQLAdapter,
        max_concurrent_jobs: int = 3
    ):
        """Initialize the job orchestration service.
        
        Args:
            docker_job_executor: Docker job executor for container operations
            result_processing_service: Service for result processing
            queue_adapter: Queue adapter for job queuing
            database_adapter: Database adapter for persistence
            max_concurrent_jobs: Maximum number of concurrent jobs
        """
        self.docker_job_executor = docker_job_executor
        self.result_processing_service = result_processing_service
        self.queue_adapter = queue_adapter
        self.database_adapter = database_adapter
        self.max_concurrent_jobs = max_concurrent_jobs
        self.active_jobs: Dict[UUID, JobExecution] = {}
        self.logger = logging.getLogger(__name__)
    
    async def start_worker(self) -> None:
        """Start the worker loop."""
        self.logger.info("Worker loop started, polling queue...")
        iteration = 0
        while True:
            try:
                iteration += 1
                if iteration % 10 == 0:  # Log every 10 iterations
                    self.logger.debug(f"Worker loop iteration {iteration}, active jobs: {len(self.active_jobs)}")
                
                # Check for new jobs
                await self._process_queue()
                
                # Check for completed jobs
                await self._check_completed_jobs()
                
                # Wait before next iteration
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error in worker loop: {e}", exc_info=True)
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _process_queue(self) -> None:
        """Process jobs from the queue."""
        try:
            # Check if we can start more jobs
            if len(self.active_jobs) >= self.max_concurrent_jobs:
                self.logger.debug(f"Max concurrent jobs reached ({len(self.active_jobs)}/{self.max_concurrent_jobs}), skipping queue check")
                return
            
            # Get next job from queue
            self.logger.debug("Polling queue for jobs...")
            try:
                job_data = await self.queue_adapter.pop_job()
                if not job_data:
                    self.logger.debug("No job available in queue")
                    return
            except Exception as e:
                self.logger.error(f"Error calling pop_job: {e}", exc_info=True)
                return
            
            self.logger.info(f"Found job in queue: scan_id={job_data.get('scan_id')}")
            
            # Create job execution
            try:
                job_execution = await self._create_job_execution(job_data)
                self.logger.info(f"Created job execution: {job_execution.id} for scan {job_execution.scan_id}")
            except Exception as e:
                self.logger.error(f"Error creating job execution: {e}", exc_info=True)
                return
            
            # Start job execution
            try:
                self.active_jobs[job_execution.id] = job_execution
                asyncio.create_task(self._execute_job_wrapper(job_execution))
                self.logger.info(f"Started job execution: {job_execution.id}")
            except Exception as e:
                self.logger.error(f"Error starting job execution: {e}", exc_info=True)
                # Remove from active jobs if we failed to start
                self.active_jobs.pop(job_execution.id, None)
            
        except Exception as e:
            self.logger.error(f"Unexpected error processing queue: {e}", exc_info=True)
    
    async def _create_job_execution(self, job_data: Dict[str, Any]) -> JobExecution:
        """Create a job execution from job data.
        
        Args:
            job_data: Job data from queue
            
        Returns:
            Job execution
        """
        try:
            from worker.domain.job_execution.entities.container_spec import ContainerSpec
            
            # Extract job information
            scan_id = UUID(job_data['scan_id'])
            job_type = job_data['job_type']
            target = job_data['target']
            
            image = job_data.get('image')
            if not image:
                raise ValueError("image is required in queue message but not provided. Backend must set image.")
            
            # ENTERPRISE: Worker determines paths from OWN environment variables (generic, portable)
            # This allows different deployment scenarios (Docker, K8s, etc.) without code changes
            # Host paths (from HOST's perspective - used for volume mounting to Scanner containers)
            # NOTE: Logs are part of Results - Scanner creates results/{scan_id}/logs/ automatically
            # 
            # WHY ABSOLUTE PATH?
            # - Worker creates Scanner containers dynamically via Docker API
            # - Docker API requires ABSOLUTE paths for volume mounts (Docker limitation)
            # - This path is on the HOST, not in the Worker container
            # - Example: /home/user/project/results -> Scanner sees /app/results
            results_dir_host = os.environ.get("RESULTS_DIR_HOST")
            if not results_dir_host:
                raise ValueError("RESULTS_DIR_HOST environment variable is required but not set. Worker must set this.")
            
            # Validate that path is absolute (Docker API requirement)
            if not os.path.isabs(results_dir_host):
                raise ValueError(
                    f"RESULTS_DIR_HOST must be an absolute path (Docker API requirement). "
                    f"Got: {results_dir_host}. Use ${PWD}/results in docker-compose.yml"
                )
            
            # Container paths (what Scanner container sees inside - passed via environment variables)
            results_dir_container = os.environ.get("RESULTS_DIR_CONTAINER")
            if not results_dir_container:
                raise ValueError("RESULTS_DIR_CONTAINER environment variable is required but not set. Worker must set this.")
            
            self.logger.debug(f"Using host path - results: {results_dir_host}")
            self.logger.debug(f"Using container path - results: {results_dir_container}")
            
            # Validate path is a string
            if not isinstance(results_dir_host, str):
                raise ValueError(f"Environment variable RESULTS_DIR_HOST must be a string")
            
            scan_type = job_data.get('scan_type')
            if not scan_type:
                raise ValueError("scan_type is required in queue message but not provided. Backend must set scan_type.")
            
            target_type = job_data.get('target_type')
            if not target_type:
                raise ValueError("target_type is required in queue message but not provided. Backend must determine target_type.")
            
            target_mount_path = job_data.get('target_mount_path')
            
            # Validate target_mount_path is a string if provided
            if target_mount_path is not None and not isinstance(target_mount_path, str):
                if isinstance(target_mount_path, dict):
                    target_mount_path = target_mount_path.get('path')
                else:
                    target_mount_path = str(target_mount_path)
                self.logger.warning(f"target_mount_path was not a string, converted to: {target_mount_path}")
            
            finding_policy = job_data.get('finding_policy')
            collect_metadata = job_data.get('collect_metadata')
            if collect_metadata is None:
                collect_metadata = False  # Optional: not set or null = no metadata collection
            else:
                collect_metadata = bool(collect_metadata)
            exclude_paths = job_data.get('exclude_paths')
            git_branch = job_data.get('git_branch')
            asset_volumes = job_data.get('asset_volumes', [])  # Asset volumes from scanner manifests (backend provides)
            scanners = job_data.get('scanners', [])  # Selected scanners from backend (if empty, scanner filters by scan_type)
            scanner_tool_overrides_json = job_data.get("scanner_tool_overrides_json") or "{}"
            if not isinstance(scanner_tool_overrides_json, str):
                scanner_tool_overrides_json = json.dumps(scanner_tool_overrides_json or {})
            
            # Create container specification
            # Pass host paths for volume mounting, container paths for environment variables
            # NOTE: Logs are part of Results - Scanner creates results/{scan_id}/logs/ automatically
            container_spec = ContainerSpec.from_scan_config(
                image=image,
                target=target,
                results_dir=results_dir_host,  # Host path for volume mount
                scan_id=str(scan_id),
                scan_type=scan_type,
                target_type=target_type,  # Pass target_type from queue message (git_repo, local_mount, etc.)
                target_mount_path=target_mount_path,
                finding_policy=finding_policy,
                collect_metadata=collect_metadata,
                exclude_paths=exclude_paths,
                git_branch=git_branch,
                results_dir_container=results_dir_container,  # Container path (for Scanner env vars)
                asset_volumes=asset_volumes,  # Asset volumes from scanner manifests
                scanners=scanners,  # Selected scanners from backend (if empty, scanner filters by scan_type)
                scanner_tool_overrides_json=scanner_tool_overrides_json,
            )
            
            # Create job execution
            job_id_str = job_data.get('job_id')
            if not job_id_str:
                raise ValueError("job_id is required in queue message but not provided. Backend must set job_id.")
            
            job_execution = JobExecution(
                id=UUID(job_id_str),
                scan_id=scan_id,
                job_type=job_type,
                container_spec=container_spec
            )
            
            # Save to database
            await self._save_job_execution(job_execution)
            
            return job_execution
            
        except Exception as e:
            self.logger.error(f"Error creating job execution: {e}")
            raise
    
    async def _execute_job_wrapper(self, job_execution: JobExecution) -> None:
        """Wrapper for job execution with error handling.
        
        Args:
            job_execution: Job execution to execute
        """
        try:
            # Execute job
            result = await self.docker_job_executor.execute_job(job_execution)
            
            # Process results
            await self.result_processing_service.process_execution_result(result)
            
            # Update job status
            await self._update_job_status(job_execution.id, JobExecutionStatus.COMPLETED)
            
            # Remove from active jobs
            self.active_jobs.pop(job_execution.id, None)
            
            self.logger.info(f"Completed job execution: {job_execution.id}")
            
        except Exception as e:
            self.logger.error(f"Error executing job {job_execution.id}: {e}")
            
            # Update job status to failed
            await self._update_job_status(job_execution.id, JobExecutionStatus.FAILED, str(e))
            
            # Remove from active jobs
            self.active_jobs.pop(job_execution.id, None)
    
    async def _check_completed_jobs(self) -> None:
        """Check for completed jobs and clean up."""
        try:
            completed_jobs = []
            
            for job_id, job_execution in self.active_jobs.items():
                if job_execution.is_completed:
                    completed_jobs.append(job_id)
            
            # Remove completed jobs
            for job_id in completed_jobs:
                self.active_jobs.pop(job_id, None)
                
        except Exception as e:
            self.logger.error(f"Error checking completed jobs: {e}")
    
    async def stop_job_execution(self, job_id: UUID) -> bool:
        """Stop a running job execution.
        
        Args:
            job_id: Job execution ID
            
        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            job_execution = self.active_jobs.get(job_id)
            if job_execution and job_execution.is_running:
                success = await self.docker_job_executor.stop_job_execution(job_execution)
                if success:
                    await self._update_job_status(job_id, JobExecutionStatus.CANCELLED)
                return success
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error stopping job execution {job_id}: {e}")
            return False

    async def stop_job_by_scan_id(self, scan_id: str) -> bool:
        """Stop the active job for the given scan_id, if any.
        
        Args:
            scan_id: Scan ID (string UUID)
            
        Returns:
            True if a job was found and stopped, False otherwise
        """
        try:
            scan_uuid = UUID(scan_id)
            for job_id, job_execution in list(self.active_jobs.items()):
                if job_execution.scan_id == scan_uuid:
                    return await self.stop_job_execution(job_id)
            return False
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Invalid scan_id for stop_job_by_scan_id: {scan_id} ({e})")
            return False
        except Exception as e:
            self.logger.error(f"Error stopping job by scan_id {scan_id}: {e}")
            return False
    
    async def get_job_status(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        """Get job execution status.
        
        Args:
            job_id: Job execution ID
            
        Returns:
            Job status information
        """
        try:
            # Check active jobs first
            job_execution = self.active_jobs.get(job_id)
            if job_execution:
                return {
                    "job_id": str(job_execution.id),
                    "scan_id": str(job_execution.scan_id),
                    "job_type": job_execution.job_type,
                    "status": job_execution.status.value,
                    "container_state": job_execution.container_state.value,
                    "started_at": job_execution.started_at.isoformat() if job_execution.started_at else None,
                    "completed_at": job_execution.completed_at.isoformat() if job_execution.completed_at else None,
                    "error_message": job_execution.error_message,
                    "container_id": job_execution.container_id,
                    "execution_time_seconds": job_execution.execution_time_seconds,
                    "logs_count": len(job_execution.logs),
                    "is_running": job_execution.is_running,
                    "is_completed": job_execution.is_completed
                }
            
            # Check database for completed jobs
            return await self._get_job_status_from_db(job_id)
            
        except Exception as e:
            self.logger.error(f"Error getting job status for {job_id}: {e}")
            return None
    
    async def get_active_jobs(self) -> List[Dict[str, Any]]:
        """Get all active job executions.
        
        Returns:
            List of active job statuses
        """
        try:
            return [await self.get_job_status(job_id) for job_id in self.active_jobs.keys()]
            
        except Exception as e:
            self.logger.error(f"Error getting active jobs: {e}")
            return []
    
    async def get_job_history(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get job execution history.
        
        Args:
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip
            
        Returns:
            List of job execution histories
        """
        try:
            # This would typically query the database
            # For now, return active jobs
            return await self.get_active_jobs()
            
        except Exception as e:
            self.logger.error(f"Error getting job history: {e}")
            return []
    
    async def _save_job_execution(self, job_execution: JobExecution) -> None:
        """Save job execution to database.
        
        Args:
            job_execution: Job execution to save
        """
        try:
            # This would save to the database
            # Implementation depends on database adapter
            pass
            
        except Exception as e:
            self.logger.error(f"Error saving job execution: {e}")
            raise
    
    async def _update_job_status(self, job_id: UUID, status: JobExecutionStatus, error_message: Optional[str] = None) -> None:
        """Update job execution status.
        
        Args:
            job_id: Job execution ID
            status: New status
            error_message: Optional error message
        """
        try:
            # This would update the database
            # Implementation depends on database adapter
            pass
            
        except Exception as e:
            self.logger.error(f"Error updating job status: {e}")
            raise
    
    async def _get_job_status_from_db(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        """Get job status from database.
        
        Args:
            job_id: Job execution ID
            
        Returns:
            Job status information
        """
        try:
            # This would query the database
            # Implementation depends on database adapter
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting job status from database: {e}")
            return None