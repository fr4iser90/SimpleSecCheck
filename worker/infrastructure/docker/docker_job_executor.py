"""
Docker job executor for the worker infrastructure.

Handles the lifecycle of containers including creation, execution, monitoring, and cleanup.
"""

import logging
import subprocess
import time
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime
from pathlib import Path

from worker.domain.job_execution.entities.job_execution import JobExecution, JobExecutionStatus, ContainerState
from worker.domain.job_execution.entities.container_spec import ContainerSpec
from worker.domain.job_execution.entities.execution_result import ExecutionResult
from worker.infrastructure.docker_adapter import DockerAdapter


class DockerJobExecutor:
    """Service for managing container execution lifecycle."""
    
    def __init__(self, docker_adapter: DockerAdapter):
        """Initialize the container execution service.
        
        Args:
            docker_adapter: Docker adapter for container operations
        """
        self.docker_adapter = docker_adapter
        self.logger = logging.getLogger(__name__)
    
    async def execute_job(self, job_execution: JobExecution) -> ExecutionResult:
        """Execute a job in a container.
        
        Args:
            job_execution: Job execution to execute
            
        Returns:
            Execution result
        """
        try:
            # Start execution
            job_execution.start_execution()
            self.logger.info(f"Starting job execution: {job_execution.id}")
            
            # Create container
            container_id = await self._create_container(job_execution.container_spec)
            job_execution.container_id = container_id
            
            # Start container
            await self._start_container(container_id)
            
            # Monitor execution
            result = await self._monitor_execution(job_execution, container_id)
            
            # Cleanup
            await self._cleanup_container(container_id)
            
            # Complete execution
            job_execution.complete_execution(result.success, result.error_message)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing job {job_execution.id}: {e}")
            job_execution.complete_execution(False, str(e))
            return ExecutionResult(
                job_execution_id=job_execution.id,
                scan_id=job_execution.scan_id,
                success=False,
                error_message=str(e)
            )
    
    async def _create_container(self, container_spec: ContainerSpec) -> str:
        """Create a container from specification.
        
        Args:
            container_spec: Container specification
            
        Returns:
            Container ID
        """
        try:
            config = container_spec.to_docker_config()
            container_id = await self.docker_adapter.create_container(config)
            self.logger.info(f"Created container: {container_id}")
            return container_id
            
        except Exception as e:
            self.logger.error(f"Error creating container: {e}")
            raise
    
    async def _start_container(self, container_id: str) -> None:
        """Start a container.
        
        Args:
            container_id: Container ID
        """
        try:
            await self.docker_adapter.start_container(container_id)
            self.logger.info(f"Started container: {container_id}")
            
        except Exception as e:
            self.logger.error(f"Error starting container {container_id}: {e}")
            raise
    
    async def _monitor_execution(self, job_execution: JobExecution, container_id: str) -> ExecutionResult:
        """Monitor container execution and collect results.
        
        Args:
            job_execution: Job execution
            container_id: Container ID
            
        Returns:
            Execution result
        """
        try:
            # Get container logs
            logs = await self._get_container_logs(container_id)
            
            # Wait for container to complete
            exit_code = await self._wait_for_container(container_id)
            
            # Get container stats
            stats = await self._get_container_stats(container_id)
            
            # Collect results
            result = await self._collect_results(job_execution, container_id, logs, exit_code, stats)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error monitoring execution for container {container_id}: {e}")
            raise
    
    async def _get_container_logs(self, container_id: str) -> List[str]:
        """Get container logs.
        
        Args:
            container_id: Container ID
            
        Returns:
            List of log lines
        """
        try:
            logs = await self.docker_adapter.get_container_logs(container_id)
            return logs.split('\n') if logs else []
            
        except Exception as e:
            self.logger.error(f"Error getting logs for container {container_id}: {e}")
            return []
    
    async def _wait_for_container(self, container_id: str, timeout: int = 3600) -> int:
        """Wait for container to complete execution.
        
        Args:
            container_id: Container ID
            timeout: Timeout in seconds
            
        Returns:
            Container exit code
        """
        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                state = await self.docker_adapter.get_container_state(container_id)
                if state in ['exited', 'dead']:
                    return await self.docker_adapter.get_container_exit_code(container_id)
                await asyncio.sleep(1)
            
            # Timeout reached
            await self.docker_adapter.stop_container(container_id)
            raise TimeoutError(f"Container {container_id} timed out after {timeout} seconds")
            
        except Exception as e:
            self.logger.error(f"Error waiting for container {container_id}: {e}")
            raise
    
    async def _get_container_stats(self, container_id: str) -> Dict[str, Any]:
        """Get container resource usage statistics.
        
        Args:
            container_id: Container ID
            
        Returns:
            Container statistics
        """
        try:
            return await self.docker_adapter.get_container_stats(container_id)
            
        except Exception as e:
            self.logger.error(f"Error getting stats for container {container_id}: {e}")
            return {}
    
    async def _collect_results(self, job_execution: JobExecution, container_id: str, logs: List[str], exit_code: int, stats: Dict[str, Any]) -> ExecutionResult:
        """Collect execution results from container.
        
        Args:
            job_execution: Job execution
            container_id: Container ID
            logs: Container logs
            exit_code: Container exit code
            stats: Container statistics
            
        Returns:
            Execution result
        """
        try:
            success = exit_code == 0
            error_message = None if success else f"Container exited with code {exit_code}"
            
            # Collect structured results
            structured_results = await self._collect_structured_results(job_execution, container_id)
            
            # Collect file results
            file_results = await self._collect_file_results(job_execution, container_id)
            
            # Build execution result
            result = ExecutionResult(
                job_execution_id=job_execution.id,
                scan_id=job_execution.scan_id,
                success=success,
                error_message=error_message,
                execution_time_seconds=job_execution.execution_time_seconds,
                container_logs=logs,
                structured_results=structured_results,
                file_results=file_results,
                metadata={
                    "container_id": container_id,
                    "exit_code": exit_code,
                    "container_stats": stats,
                    "execution_time_seconds": job_execution.execution_time_seconds
                }
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error collecting results for container {container_id}: {e}")
            raise
    
    async def _collect_structured_results(self, job_execution: JobExecution, container_id: str) -> Dict[str, Any]:
        """Collect structured results from container.
        
        Args:
            job_execution: Job execution
            container_id: Container ID
            
        Returns:
            Structured results
        """
        try:
            # Look for JSON results in the results directory
            results_dir = job_execution.container_spec.environment.get("PROJECT_RESULTS_DIR", "/app/results")
            json_files = await self.docker_adapter.list_files_in_container(container_id, results_dir)
            
            structured_results = {}
            for file_path in json_files:
                if file_path.endswith('.json'):
                    content = await self.docker_adapter.read_file_from_container(container_id, file_path)
                    if content:
                        try:
                            import json
                            structured_results[file_path] = json.loads(content)
                        except json.JSONDecodeError:
                            self.logger.warning(f"Invalid JSON in file: {file_path}")
            
            return structured_results
            
        except Exception as e:
            self.logger.error(f"Error collecting structured results: {e}")
            return {}
    
    async def _collect_file_results(self, job_execution: JobExecution, container_id: str) -> Dict[str, str]:
        """Collect file results from container.
        
        Args:
            job_execution: Job execution
            container_id: Container ID
            
        Returns:
            File results
        """
        try:
            # Look for result files in the results directory
            results_dir = job_execution.container_spec.environment.get("PROJECT_RESULTS_DIR", "/app/results")
            files = await self.docker_adapter.list_files_in_container(container_id, results_dir)
            
            file_results = {}
            for file_path in files:
                if not file_path.endswith('.json'):  # Skip JSON files (handled separately)
                    content = await self.docker_adapter.read_file_from_container(container_id, file_path)
                    if content:
                        file_results[file_path] = content
            
            return file_results
            
        except Exception as e:
            self.logger.error(f"Error collecting file results: {e}")
            return {}
    
    async def _cleanup_container(self, container_id: str) -> None:
        """Clean up container after execution.
        
        Args:
            container_id: Container ID
        """
        try:
            await self.docker_adapter.remove_container(container_id)
            self.logger.info(f"Removed container: {container_id}")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up container {container_id}: {e}")
            # Don't raise here - cleanup failure shouldn't fail the job
    
    async def stop_job_execution(self, job_execution: JobExecution) -> bool:
        """Stop a running job execution.
        
        Args:
            job_execution: Job execution to stop
            
        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            if job_execution.container_id:
                await self.docker_adapter.stop_container(job_execution.container_id)
                await self.docker_adapter.remove_container(job_execution.container_id)
                job_execution.cancel_execution()
                self.logger.info(f"Stopped job execution: {job_execution.id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error stopping job execution {job_execution.id}: {e}")
            return False
    
    async def get_container_status(self, container_id: str) -> Optional[Dict[str, Any]]:
        """Get container status and information.
        
        Args:
            container_id: Container ID
            
        Returns:
            Container status information
        """
        try:
            return await self.docker_adapter.get_container_info(container_id)
            
        except Exception as e:
            self.logger.error(f"Error getting container status for {container_id}: {e}")
            return None