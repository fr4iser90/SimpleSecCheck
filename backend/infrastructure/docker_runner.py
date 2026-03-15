"""
Docker Runner

This module provides Docker container management functionality for scanner execution.
"""
import asyncio
import logging
import os
import time
from typing import Dict, Any, Optional, List
from docker import DockerClient
from docker.errors import DockerException, ImageNotFound, ContainerError
from docker.models.containers import Container

from config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class DockerRunner:
    """Docker container runner for scanner execution."""
    
    def __init__(self):
        self.client: Optional[DockerClient] = None
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize Docker client."""
        try:
            self.client = DockerClient(base_url=f'unix://{settings.DOCKER_SOCKET}')
            # Test connection
            self.client.ping()
            self.is_initialized = True
            logger.info("Docker client initialized successfully")
        except DockerException as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            self.is_initialized = False
            raise
    
    async def pull_image(self, image_name: str) -> bool:
        """Pull Docker image."""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            logger.info(f"Pulling image: {image_name}")
            self.client.images.pull(image_name)
            logger.info(f"Successfully pulled image: {image_name}")
            return True
        except ImageNotFound as e:
            logger.error(f"Image not found: {image_name} - {e}")
            return False
        except DockerException as e:
            logger.error(f"Failed to pull image {image_name}: {e}")
            return False
    
    async def run_container(
        self,
        image_name: str,
        command: Optional[str] = None,
        volumes: Optional[Dict[str, Dict[str, str]]] = None,
        environment: Optional[Dict[str, str]] = None,
        network: Optional[str] = None,
        remove: bool = True,
        timeout: int = 3600,
        **kwargs
    ) -> Dict[str, Any]:
        """Run Docker container."""
        if not self.is_initialized:
            await self.initialize()
        
        container = None
        try:
            # Prepare container configuration
            container_config = {
                'image': image_name,
                'command': command,
                'volumes': volumes or {},
                'environment': environment or {},
                'network': network if network else settings.DOCKER_NETWORK,
                'remove': remove,
                'detach': True,
                **kwargs
            }
            
            logger.info(f"Starting container with image: {image_name}")
            container = self.client.containers.run(**container_config)
            
            # Wait for container to complete
            start_time = time.time()
            while True:
                container.reload()
                if container.status in ['exited', 'dead']:
                    break
                
                if time.time() - start_time > timeout:
                    logger.warning(f"Container timeout after {timeout} seconds")
                    container.stop()
                    break
                
                await asyncio.sleep(1)
            
            # Get container logs
            logs = container.logs(stdout=True, stderr=True).decode('utf-8')
            
            # Get exit code
            container.reload()
            exit_code = container.attrs['State']['ExitCode']
            
            result = {
                'container_id': container.id,
                'exit_code': exit_code,
                'logs': logs,
                'success': exit_code == 0,
                'duration': time.time() - start_time,
            }
            
            logger.info(f"Container completed: {container.id}, exit_code: {exit_code}")
            return result
            
        except ContainerError as e:
            logger.error(f"Container error: {e}")
            return {
                'container_id': container.id if container else None,
                'exit_code': -1,
                'logs': str(e),
                'success': False,
                'duration': 0,
            }
        except DockerException as e:
            logger.error(f"Docker execution error: {e}")
            return {
                'container_id': container.id if container else None,
                'exit_code': -1,
                'logs': str(e),
                'success': False,
                'duration': 0,
            }
        finally:
            # Clean up container if not set to auto-remove
            if container and not remove:
                try:
                    container.remove(force=True)
                except DockerException:
                    pass
    
    async def list_containers(self, all_containers: bool = False) -> List[Dict[str, Any]]:
        """List running containers."""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            containers = self.client.containers.list(all=all_containers)
            return [
                {
                    'id': container.id,
                    'name': container.name,
                    'status': container.status,
                    'image': container.image.tags[0] if container.image.tags else str(container.image),
                }
                for container in containers
            ]
        except DockerException as e:
            logger.error(f"Failed to list containers: {e}")
            return []
    
    async def stop_container(self, container_id: str) -> bool:
        """Stop container."""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            container = self.client.containers.get(container_id)
            container.stop()
            logger.info(f"Stopped container: {container_id}")
            return True
        except DockerException as e:
            logger.error(f"Failed to stop container {container_id}: {e}")
            return False
    
    async def remove_container(self, container_id: str) -> bool:
        """Remove container."""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            container = self.client.containers.get(container_id)
            container.remove(force=True)
            logger.info(f"Removed container: {container_id}")
            return True
        except DockerException as e:
            logger.error(f"Failed to remove container {container_id}: {e}")
            return False
    
    async def get_health(self) -> Dict[str, Any]:
        """Get Docker health status."""
        try:
            if not self.is_initialized:
                await self.initialize()
            
            info = self.client.info()
            return {
                'status': True,
                'type': 'docker',
                'version': info.get('ServerVersion', 'unknown'),
                'containers_running': info.get('ContainersRunning', 0),
                'containers_paused': info.get('ContainersPaused', 0),
                'containers_stopped': info.get('ContainersStopped', 0),
                'images': info.get('Images', 0),
                'docker_socket': settings.DOCKER_SOCKET,
                'initialized': self.is_initialized,
            }
        except DockerException as e:
            return {
                'status': False,
                'type': 'docker',
                'error': str(e),
                'initialized': self.is_initialized,
            }
    
    async def cleanup_containers(self, label: Optional[str] = None):
        """Clean up containers with optional label filter."""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            filters = {}
            if label:
                filters['label'] = label
            
            containers = self.client.containers.list(all=True, filters=filters)
            cleaned_count = 0
            
            for container in containers:
                try:
                    container.remove(force=True)
                    cleaned_count += 1
                except DockerException:
                    pass
            
            logger.info(f"Cleaned up {cleaned_count} containers")
            return cleaned_count
        except DockerException as e:
            logger.error(f"Failed to cleanup containers: {e}")
            return 0


# Global Docker runner instance
docker_runner = DockerRunner()


async def get_docker_health() -> Dict[str, Any]:
    """Get Docker health status."""
    return await docker_runner.get_health()