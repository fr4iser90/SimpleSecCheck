"""
Docker adapter for the worker infrastructure.

Provides Docker container management operations.
"""

import asyncio
import logging
import subprocess
import time
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime
from pathlib import Path

import docker
from docker.errors import DockerException, NotFound
from docker.types import HostConfig

# Use structlog for consistent logging with worker
try:
    from worker.infrastructure.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    # Fallback if structlog not available
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.ERROR)  # Only show errors if structlog not available


class DockerAdapter:
    """Adapter for Docker container operations."""
    
    def __init__(self):
        """Initialize Docker adapter."""
        self.logger = logger  # Use module-level logger
        try:
            self.client = docker.from_env()
            # Test connection
            try:
                self.client.ping()
                self.logger.info("Docker client initialized successfully")
            except Exception as ping_error:
                self.logger.warning(f"Docker client created but ping failed: {ping_error}")
                self.client = None
        except Exception as e:
            # Use error() method that works with both structlog and standard logging
            if hasattr(self.logger, 'error'):
                self.logger.error("Failed to initialize Docker client", error=str(e), exc_info=True)
            else:
                self.logger.error(f"Failed to initialize Docker client: {e}", exc_info=True)
            
            # Check if docker socket exists
            import os
            docker_sock = "/var/run/docker.sock"
            if os.path.exists(docker_sock):
                sock_stat = os.stat(docker_sock)
                sock_mode = oct(sock_stat.st_mode)
                sock_uid = sock_stat.st_uid
                sock_gid = sock_stat.st_gid
                if hasattr(logger, 'error'):
                    logger.error(
                        "Docker socket exists but client failed",
                        socket_path=docker_sock,
                        permissions=sock_mode,
                        uid=sock_uid,
                        gid=sock_gid
                    )
                else:
                    logger.error(f"Docker socket exists but client failed. Socket: {docker_sock}, permissions: {sock_mode}, uid: {sock_uid}, gid: {sock_gid}")
            else:
                if hasattr(logger, 'error'):
                    logger.error("Docker socket not found", socket_path=docker_sock)
                else:
                    logger.error(f"Docker socket not found at {docker_sock}")
            self.client = None
    
    async def create_container(self, config: Dict[str, Any]) -> str:
        """Create a container.
        
        Args:
            config: Container configuration (may contain host_config)
            
        Returns:
            Container ID
        """
        try:
            # Check if container with same name exists and remove it
            container_name = config.get("name")
            if container_name:
                try:
                    existing = await asyncio.to_thread(
                        self.client.containers.get,
                        container_name
                    )
                    # Container exists - remove it
                    self.logger.warning(f"Container {container_name} already exists, removing it")
                    try:
                        if existing.status == "running":
                            await asyncio.to_thread(existing.stop)
                        await asyncio.to_thread(existing.remove)
                        self.logger.info(f"Removed existing container {container_name}")
                    except Exception as remove_error:
                        self.logger.warning(f"Could not remove existing container {container_name}: {remove_error}")
                except NotFound:
                    # Container doesn't exist - that's fine
                    pass
                except Exception as check_error:
                    self.logger.warning(f"Error checking for existing container {container_name}: {check_error}")
            
            # Extract host_config if present
            host_config_dict = config.pop("host_config", None)
            
            # Docker 7.x API: containers.create() expects parameters directly, not host_config
            # Extract host_config parameters and merge into main config
            if host_config_dict:
                # Extract binds (volumes) and convert to volumes format
                if "binds" in host_config_dict:
                    # Convert binds to volumes dict format: {"/host/path": {"bind": "/container/path", "mode": "rw"}}
                    volumes = {}
                    for bind_string in host_config_dict["binds"]:
                        # Format: "/host/path:/container/path:rw"
                        parts = bind_string.split(":")
                        if len(parts) >= 2:
                            host_path = parts[0]
                            container_path = parts[1]
                            mode = parts[2] if len(parts) > 2 else "rw"
                            volumes[host_path] = {"bind": container_path, "mode": mode}
                    config["volumes"] = volumes
                
                # Extract other host_config parameters
                if "privileged" in host_config_dict:
                    config["privileged"] = host_config_dict["privileged"]
                if "read_only" in host_config_dict:
                    config["read_only"] = host_config_dict["read_only"]
                if "tmpfs" in host_config_dict:
                    config["tmpfs"] = host_config_dict["tmpfs"]
                if "cpu_quota" in host_config_dict:
                    config["cpu_quota"] = host_config_dict["cpu_quota"]
                if "cpu_period" in host_config_dict:
                    config["cpu_period"] = host_config_dict["cpu_period"]
                if "mem_limit" in host_config_dict:
                    config["mem_limit"] = host_config_dict["mem_limit"]
                if host_config_dict.get("init"):
                    config["init"] = True
                if "restart_policy" in host_config_dict:
                    config["restart_policy"] = host_config_dict["restart_policy"]
                if "port_bindings" in host_config_dict:
                    config["ports"] = host_config_dict["port_bindings"]
            
            # Create container with merged config
            container = await asyncio.to_thread(
                self.client.containers.create,
                **config
            )
            return container.id
        except DockerException as e:
            logger.error(f"Error creating container: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating container: {e}", exc_info=True)
            raise
    
    async def start_container(self, container_id: str) -> None:
        """Start a container.
        
        Args:
            container_id: Container ID
        """
        try:
            container = await asyncio.to_thread(
                self.client.containers.get,
                container_id
            )
            await asyncio.to_thread(container.start)
        except DockerException as e:
            self.logger.error(f"Error starting container {container_id}: {e}")
            raise
    
    async def stop_container(self, container_id: str) -> None:
        """Stop a container.
        
        Args:
            container_id: Container ID
        """
        try:
            container = await asyncio.to_thread(
                self.client.containers.get,
                container_id
            )
            # Longer timeout so tools (Checkov, CodeQL, …) can SIGTERM children before SIGKILL
            await asyncio.to_thread(container.stop, timeout=45)
        except DockerException as e:
            self.logger.error(f"Error stopping container {container_id}: {e}")
            raise
    
    async def remove_container(self, container_id: str) -> None:
        """Remove a container.
        
        Args:
            container_id: Container ID
        """
        try:
            container = await asyncio.to_thread(
                self.client.containers.get,
                container_id
            )
            await asyncio.to_thread(container.remove)
        except DockerException as e:
            self.logger.error(f"Error removing container {container_id}: {e}")
            # Don't raise here - cleanup failure shouldn't fail the job
    
    async def get_container_logs(self, container_id: str) -> str:
        """Get container logs.
        
        Args:
            container_id: Container ID
            
        Returns:
            Container logs
        """
        try:
            container = await asyncio.to_thread(
                self.client.containers.get,
                container_id
            )
            logs = await asyncio.to_thread(
                container.logs,
                stdout=True,
                stderr=True,
                timestamps=True
            )
            return logs.decode('utf-8') if logs else ""
        except DockerException as e:
            self.logger.error(f"Error getting logs for container {container_id}: {e}")
            return ""
    
    async def get_container_state(self, container_id: str) -> str:
        """Get container state.
        
        Args:
            container_id: Container ID
            
        Returns:
            Container state
        """
        try:
            container = await asyncio.to_thread(
                self.client.containers.get,
                container_id
            )
            return container.status
        except DockerException as e:
            self.logger.error(f"Error getting state for container {container_id}: {e}")
            return "unknown"
    
    async def get_container_exit_code(self, container_id: str) -> int:
        """Get container exit code.
        
        Args:
            container_id: Container ID
            
        Returns:
            Container exit code
        """
        try:
            container = await asyncio.to_thread(
                self.client.containers.get,
                container_id
            )
            return container.attrs['State']['ExitCode']
        except DockerException as e:
            self.logger.error(f"Error getting exit code for container {container_id}: {e}")
            return -1
    
    async def get_container_stats(self, container_id: str) -> Dict[str, Any]:
        """Get container resource usage statistics.
        
        Args:
            container_id: Container ID
            
        Returns:
            Container statistics
        """
        try:
            container = await asyncio.to_thread(
                self.client.containers.get,
                container_id
            )
            stats = await asyncio.to_thread(container.stats, stream=False)
            return {
                "cpu_usage": stats.get('cpu_stats', {}),
                "memory_usage": stats.get('memory_stats', {}),
                "network_io": stats.get('networks', {}),
                "block_io": stats.get('blkio_stats', {})
            }
        except DockerException as e:
            self.logger.error(f"Error getting stats for container {container_id}: {e}")
            return {}
    
    async def list_files_in_container(self, container_id: str, path: str) -> List[str]:
        """List files in a container.
        
        Args:
            container_id: Container ID
            path: Path to list
            
        Returns:
            List of file paths
        """
        try:
            container = await asyncio.to_thread(
                self.client.containers.get,
                container_id
            )
            result = await asyncio.to_thread(
                container.exec_run,
                f"find {path} -type f 2>/dev/null",
                stdout=True,
                stderr=True
            )
            if result.exit_code == 0:
                return result.output.decode('utf-8').strip().split('\n')
            return []
        except DockerException as e:
            self.logger.error(f"Error listing files in container {container_id}: {e}")
            return []
    
    async def read_file_from_container(self, container_id: str, file_path: str) -> Optional[str]:
        """Read a file from a container.
        
        Args:
            container_id: Container ID
            file_path: File path
            
        Returns:
            File content
        """
        try:
            container = await asyncio.to_thread(
                self.client.containers.get,
                container_id
            )
            result = await asyncio.to_thread(
                container.exec_run,
                f"cat '{file_path}'",
                stdout=True,
                stderr=True
            )
            if result.exit_code == 0:
                return result.output.decode('utf-8')
            return None
        except DockerException as e:
            self.logger.error(f"Error reading file from container {container_id}: {e}")
            return None
    
    async def get_container_info(self, container_id: str) -> Optional[Dict[str, Any]]:
        """Get container information.
        
        Args:
            container_id: Container ID
            
        Returns:
            Container information
        """
        try:
            container = await asyncio.to_thread(
                self.client.containers.get,
                container_id
            )
            return {
                "id": container.id,
                "name": container.name,
                "image": container.image.tags[0] if container.image.tags else str(container.image),
                "status": container.status,
                "created": container.attrs['Created'],
                "labels": container.labels,
                "ports": container.ports,
                "mounts": container.attrs['Mounts']
            }
        except DockerException as e:
            self.logger.error(f"Error getting container info for {container_id}: {e}")
            return None