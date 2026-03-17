"""
Docker job executor for the worker infrastructure.

Handles the lifecycle of containers including creation, execution, monitoring, and cleanup.
"""

import asyncio
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
    
    def __init__(self, docker_adapter: DockerAdapter, database_adapter=None):
        """Initialize the container execution service.
        
        Args:
            docker_adapter: Docker adapter for container operations
            database_adapter: Optional database adapter for status updates
        """
        self.docker_adapter = docker_adapter
        self.database_adapter = database_adapter
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
            
            # Update scan status to running in database
            try:
                from worker.domain.job_execution.services.result_processing_service import update_scan_status_to_running
                # Get database adapter from job_execution or inject it
                # For now, we'll need to pass it through - check if it's available
                if hasattr(self, 'database_adapter') and self.database_adapter:
                    await update_scan_status_to_running(self.database_adapter, str(job_execution.scan_id))
            except Exception as e:
                self.logger.warning(f"Failed to update scan status to running: {e}")
                # Don't fail the job execution if status update fails
            
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
        """Collect structured results from mounted volume (host filesystem).
        
        Args:
            job_execution: Job execution
            container_id: Container ID (not used, kept for compatibility)
            
        Returns:
            Structured results
        """
        try:
            import json
            import os
            from pathlib import Path
            
            # Extract results directory container path from volume mounts (GENERIC)
            # Find volume mount that contains results - don't hardcode container path!
            # FIX: Use container_path, not host_path, because Worker runs in a container
            # Both Worker and Scanner containers mount the same volume to /app/results
            results_dir = None
            for volume in job_execution.container_spec.volumes:
                # Look for volume that mounts to results directory in container
                # This is generic - works with any container path configuration
                if "results" in volume.container_path.lower() or volume.container_path.endswith("/results"):
                    results_dir = volume.container_path  # Use container path, not host path
                    self.logger.debug(f"Found results volume mount: {volume.host_path} -> {volume.container_path}, using container path: {results_dir}")
                    break
            
            if not results_dir:
                raise ValueError("results_dir is required but not provided")
            
            # Ensure results_dir is a string and exists
            if not isinstance(results_dir, str):
                self.logger.warning(f"results_dir is not a string: {type(results_dir)}, skipping file collection")
                return {}
            
            # Get scan_id from job execution
            scan_id = str(job_execution.scan_id)
            
            # Look in scan-specific directory: {results_dir}/{scan_id}/tools/
            scan_results_path = Path(results_dir) / scan_id / "tools"
            
            if not scan_results_path.exists():
                self.logger.warning(f"Tools directory does not exist: {scan_results_path}")
                return {}
            
            structured_results = {}
            
            # Iterate through tool directories
            for tool_dir in scan_results_path.iterdir():
                if not tool_dir.is_dir():
                    continue
                
                tool_name = tool_dir.name
                report_file = tool_dir / "report.json"
                
                if report_file.exists():
                    try:
                        content = await asyncio.to_thread(report_file.read_text, encoding="utf-8")
                        if content:
                            structured_results[tool_name] = json.loads(content)
                    except json.JSONDecodeError:
                        self.logger.warning(f"Invalid JSON in file: {report_file}")
                    except Exception as e:
                        self.logger.warning(f"Error reading file {report_file}: {e}")
            
            # Post-policy statistics (written by generate-html-report.py): use for DB so false positives are not counted
            stats_file = Path(results_dir) / scan_id / "summary" / "statistics.json"
            if stats_file.exists():
                try:
                    stats_content = await asyncio.to_thread(stats_file.read_text, encoding="utf-8")
                    if stats_content:
                        structured_results["_post_policy_statistics"] = json.loads(stats_content)
                        self.logger.debug(f"Using post-policy statistics from {stats_file}")
                except (json.JSONDecodeError, OSError) as e:
                    self.logger.warning(f"Could not read post-policy statistics from {stats_file}: {e}")
            
            return structured_results
            
        except Exception as e:
            self.logger.error(f"Error collecting structured results: {e}")
            return {}
    
    async def _collect_file_results(self, job_execution: JobExecution, container_id: str) -> Dict[str, str]:
        """Collect file results from mounted volume (host filesystem).
        
        Args:
            job_execution: Job execution
            container_id: Container ID (not used, kept for compatibility)
            
        Returns:
            File results
        """
        try:
            import os
            from pathlib import Path
            
            # Extract results directory container path from volume mounts (GENERIC)
            # Find volume mount that contains results - don't hardcode container path!
            # FIX: Use container_path, not host_path, because Worker runs in a container
            # Both Worker and Scanner containers mount the same volume to /app/results
            results_dir = None
            for volume in job_execution.container_spec.volumes:
                # Look for volume that mounts to results directory in container
                # This is generic - works with any container path configuration
                if "results" in volume.container_path.lower() or volume.container_path.endswith("/results"):
                    results_dir = volume.container_path  # Use container path, not host path
                    self.logger.debug(f"Found results volume mount: {volume.host_path} -> {volume.container_path}, using container path: {results_dir}")
                    break
            
            if not results_dir:
                raise ValueError("results_dir is required but not provided")
            
            # Ensure results_dir is a string and exists
            if not isinstance(results_dir, str):
                self.logger.warning(f"results_dir is not a string: {type(results_dir)}, skipping file collection")
                return {}
            
            results_path = Path(results_dir)
            if not results_path.exists():
                self.logger.warning(f"Results directory does not exist: {results_dir}")
                return {}
            
            file_results = {}
            
            # Find all non-JSON files in the results directory
            for file_path in results_path.rglob("*"):
                if file_path.is_file() and not file_path.suffix == '.json':
                    try:
                        content = await asyncio.to_thread(file_path.read_text, encoding="utf-8", errors='ignore')
                        if content:
                            file_results[str(file_path.relative_to(results_path))] = content
                    except Exception as e:
                        self.logger.warning(f"Error reading file {file_path}: {e}")
            
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