"""
Scan Orchestration Service

This service orchestrates the execution of security scans by coordinating
between the scan management, queue management, and scanner execution.
"""
from typing import List, Dict, Any, Optional
import asyncio
import logging
from datetime import datetime

from domain.entities.scan import Scan, ScanStatus, ScanType
from domain.entities.target_type import TargetType
from infrastructure.redis.client import redis_client
from infrastructure.docker_runner import docker_runner
from config.scanner_config import get_scanner_config

logger = logging.getLogger(__name__)


class ScanOrchestrationService:
    """Service for orchestrating scan execution."""
    
    def __init__(self):
        self.scanner_config = get_scanner_config()
        
    async def create_scan(
        self,
        name: str,
        description: str,
        scan_type: ScanType,
        target_url: str,
        target_type: str,
        scanners: List[str],
        config: Dict[str, Any] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Scan:
        """Create a new scan."""
        scan = Scan(
            name=name,
            description=description,
            scan_type=scan_type,
            target_url=target_url,
            target_type=target_type,
            scanners=scanners,
            config=config or {},
            user_id=user_id,
            project_id=project_id,
        )
        
        # Store scan in Redis
        await self._store_scan(scan)
        
        logger.info(f"Created scan {scan.id} for target {target_url}")
        return scan
    
    async def start_scan(self, scan_id: str) -> bool:
        """Start a scan execution."""
        scan = await self._get_scan(scan_id)
        if not scan:
            logger.error(f"Scan {scan_id} not found")
            return False
        
        if scan.status != ScanStatus.PENDING:
            logger.error(f"Scan {scan_id} cannot be started from status {scan.status}")
            return False
        
        # Update scan status to running
        scan.start()
        await self._store_scan(scan)
        
        # Queue scan for execution
        await self._queue_scan(scan)
        
        logger.info(f"Started scan {scan_id}")
        return True
    
    async def execute_scan(self, scan_id: str) -> bool:
        """Execute a scan."""
        scan = await self._get_scan(scan_id)
        if not scan:
            logger.error(f"Scan {scan_id} not found")
            return False
        
        if scan.status != ScanStatus.RUNNING:
            logger.error(f"Scan {scan_id} cannot be executed from status {scan.status}")
            return False
        
        try:
            # Execute each scanner
            results = []
            total_duration = 0
            
            for scanner_name in scan.scanners:
                scanner_result = await self._execute_scanner(scan, scanner_name)
                results.append(scanner_result)
                total_duration += scanner_result.get('duration', 0)
            
            # Complete scan
            scan.complete(results, total_duration)
            await self._store_scan(scan)
            
            # Publish completion event
            await self._publish_scan_completion(scan)
            
            logger.info(f"Completed scan {scan_id} successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute scan {scan_id}: {e}")
            scan.fail(str(e))
            await self._store_scan(scan)
            return False
    
    async def cancel_scan(self, scan_id: str) -> bool:
        """Cancel a running scan."""
        scan = await self._get_scan(scan_id)
        if not scan:
            logger.error(f"Scan {scan_id} not found")
            return False
        
        if scan.status != ScanStatus.RUNNING:
            logger.error(f"Scan {scan_id} cannot be cancelled from status {scan.status}")
            return False
        
        # Cancel scan
        scan.cancel()
        await self._store_scan(scan)
        
        # Stop any running containers
        await self._stop_scan_containers(scan_id)
        
        logger.info(f"Cancelled scan {scan_id}")
        return True
    
    async def get_scan(self, scan_id: str) -> Optional[Scan]:
        """Get scan by ID."""
        return await self._get_scan(scan_id)
    
    async def list_scans(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        status: Optional[ScanStatus] = None,
        scan_type: Optional[ScanType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Scan]:
        """List scans with optional filtering."""
        # This would typically query a database
        # For now, return empty list as we don't have persistence implemented
        return []
    
    async def retry_scan(self, scan_id: str) -> bool:
        """Retry a failed scan."""
        scan = await self._get_scan(scan_id)
        if not scan:
            logger.error(f"Scan {scan_id} not found")
            return False
        
        if scan.status != ScanStatus.FAILED:
            logger.error(f"Scan {scan_id} cannot be retried from status {scan.status}")
            return False
        
        scan.retry()
        await self._store_scan(scan)
        
        # Queue scan for execution
        await self._queue_scan(scan)
        
        logger.info(f"Retried scan {scan_id}")
        return True
    
    async def _execute_scanner(self, scan: Scan, scanner_name: str) -> Dict[str, Any]:
        """Execute a single scanner."""
        scanner_config = self.scanner_config.get(scanner_name)
        if not scanner_config or not scanner_config.get('enabled', False):
            logger.warning(f"Scanner {scanner_name} is not enabled or configured")
            return {
                'scanner': scanner_name,
                'status': 'skipped',
                'message': 'Scanner not enabled',
                'duration': 0,
                'vulnerabilities': [],
            }
        
        try:
            # Prepare scanner execution
            image_name = scanner_config['docker_image']
            timeout = scanner_config.get('timeout', 600)
            
            # Prepare volumes and environment
            volumes = self._prepare_volumes(scan)
            environment = self._prepare_environment(scan, scanner_name)
            
            # Execute scanner container
            result = await docker_runner.run_container(
                image_name=image_name,
                volumes=volumes,
                environment=environment,
                timeout=timeout,
            )
            
            # Process results
            vulnerabilities = self._parse_scanner_results(result['logs'], scanner_name)
            
            return {
                'scanner': scanner_name,
                'status': 'completed' if result['success'] else 'failed',
                'message': result['logs'],
                'duration': result['duration'],
                'vulnerabilities': vulnerabilities,
                'exit_code': result['exit_code'],
            }
            
        except Exception as e:
            logger.error(f"Failed to execute scanner {scanner_name}: {e}")
            return {
                'scanner': scanner_name,
                'status': 'failed',
                'message': str(e),
                'duration': 0,
                'vulnerabilities': [],
            }
    
    def _prepare_volumes(self, scan: Scan) -> Dict[str, Dict[str, str]]:
        """Prepare volume mappings for scanner execution."""
        volumes = {}
        
        # Map target directory
        if scan.target_type == TargetType.GIT_REPO.value:
            volumes[scan.target_url] = {
                'bind': '/target',
                'mode': 'ro'
            }
        
        # Map results directory
        volumes[f'/results/{scan.id}'] = {
            'bind': '/results',
            'mode': 'rw'
        }
        
        return volumes
    
    def _prepare_environment(self, scan: Scan, scanner_name: str) -> Dict[str, str]:
        """Prepare environment variables for scanner execution."""
        env = {
            'SCAN_ID': scan.id,
            'SCAN_NAME': scan.name,
            'TARGET_URL': scan.target_url,
            'TARGET_TYPE': scan.target_type,
            'SCANNER_NAME': scanner_name,
            'RESULTS_DIR': '/results',
        }
        
        # Add scanner-specific configuration
        scanner_config = self.scanner_config.get(scanner_name, {})
        for key, value in scanner_config.get('config', {}).items():
            env[f'SCANNER_{key.upper()}'] = str(value)
        
        return env
    
    def _parse_scanner_results(self, logs: str, scanner_name: str) -> List[Dict[str, Any]]:
        """Parse scanner results from logs."""
        # This would implement scanner-specific result parsing
        # For now, return empty list
        return []
    
    async def _store_scan(self, scan: Scan):
        """Store scan in Redis."""
        await redis_client.set(f"scan:{scan.id}", scan.to_dict())
    
    async def _get_scan(self, scan_id: str) -> Optional[Scan]:
        """Get scan from Redis."""
        scan_data = await redis_client.get(f"scan:{scan_id}")
        if scan_data:
            return Scan.from_dict(scan_data)
        return None
    
    async def _queue_scan(self, scan: Scan):
        """Queue scan for execution."""
        await redis_client.lpush("scan_queue", scan.id)
    
    async def _publish_scan_completion(self, scan: Scan):
        """Publish scan completion event."""
        await redis_client.publish("scan_events", {
            'type': 'scan_completed',
            'scan_id': scan.id,
            'status': scan.status.value,
            'total_vulnerabilities': scan.total_vulnerabilities,
            'duration': scan.get_duration(),
        })
    
    async def _stop_scan_containers(self, scan_id: str):
        """Stop any running containers for a scan."""
        # This would implement container cleanup
        # For now, just log
        logger.info(f"Stopping containers for scan {scan_id}")


# Global scan orchestration service instance
scan_orchestration_service = ScanOrchestrationService()