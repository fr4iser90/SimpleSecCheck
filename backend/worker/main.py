"""
Scanner Worker

This module contains the scanner worker that processes scan jobs from the queue.
The worker runs as a separate container and executes scanner jobs.
"""
import asyncio
import logging
import os
import signal
import sys
from typing import Dict, Any, Optional

from infrastructure.redis.client import redis_client
from infrastructure.docker_runner import docker_runner
from infrastructure.logging_config import setup_logging
from config.settings import get_settings

settings = get_settings()

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


class ScannerWorker:
    """Scanner worker for processing scan jobs."""
    
    def __init__(self):
        self.running = False
        self.shutdown_event = asyncio.Event()
        
    async def start(self):
        """Start the scanner worker."""
        logger.info("Starting scanner worker")
        
        # Initialize connections
        await redis_client.connect()
        await docker_runner.initialize()
        
        self.running = True
        self.shutdown_event.clear()
        
        # Start processing jobs
        await self._process_jobs()
    
    async def stop(self):
        """Stop the scanner worker."""
        logger.info("Stopping scanner worker")
        self.running = False
        self.shutdown_event.set()
        
        # Close connections
        await redis_client.disconnect()
    
    async def _process_jobs(self):
        """Process scan jobs from the queue."""
        while self.running:
            try:
                # Wait for a job from the queue
                job_data = await redis_client.brpop("scan_queue", timeout=1)
                
                if job_data:
                    scan_id = job_data[1]  # brpop returns (key, value)
                    logger.info(f"Processing scan job: {scan_id}")
                    
                    # Process the job
                    await self._process_scan_job(scan_id)
                
            except Exception as e:
                logger.error(f"Error processing job: {e}")
                await asyncio.sleep(1)  # Wait before retrying
    
    async def _process_scan_job(self, scan_id: str):
        """Process a single scan job."""
        try:
            # Get scan details from Redis
            scan_data = await redis_client.get(f"scan:{scan_id}")
            if not scan_data:
                logger.error(f"Scan {scan_id} not found")
                return
            
            # Execute the scan
            await self._execute_scan(scan_data)
            
        except Exception as e:
            logger.error(f"Failed to process scan {scan_id}: {e}")
    
    async def _execute_scan(self, scan_data: Dict[str, Any]):
        """Execute a scan."""
        scan_id = scan_data.get('id')
        scanners = scan_data.get('scanners', [])
        target_url = scan_data.get('target_url')
        target_type = scan_data.get('target_type')
        
        logger.info(f"Executing scan {scan_id} for {target_type}: {target_url}")
        
        # Execute each scanner
        results = []
        total_duration = 0
        
        for scanner_name in scanners:
            try:
                scanner_result = await self._execute_scanner(
                    scan_id, scanner_name, target_url, target_type
                )
                results.append(scanner_result)
                total_duration += scanner_result.get('duration', 0)
                
            except Exception as e:
                logger.error(f"Failed to execute scanner {scanner_name}: {e}")
                results.append({
                    'scanner': scanner_name,
                    'status': 'failed',
                    'message': str(e),
                    'duration': 0,
                    'vulnerabilities': [],
                })
        
        # Store results
        await self._store_scan_results(scan_id, results, total_duration)
        
        # Publish completion event
        await self._publish_scan_completion(scan_id, results, total_duration)
        
        logger.info(f"Completed scan {scan_id}")
    
    async def _execute_scanner(
        self,
        scan_id: str,
        scanner_name: str,
        target_url: str,
        target_type: str
    ) -> Dict[str, Any]:
        """Execute a single scanner."""
        logger.info(f"Executing scanner {scanner_name} for scan {scan_id}")
        
        # This would implement the actual scanner execution
        # For now, return a mock result
        return {
            'scanner': scanner_name,
            'status': 'completed',
            'message': 'Scanner executed successfully',
            'duration': 30,
            'vulnerabilities': [],
            'exit_code': 0,
        }
    
    async def _store_scan_results(
        self,
        scan_id: str,
        results: list,
        total_duration: int
    ):
        """Store scan results."""
        # Update scan status and results in Redis
        scan_data = await redis_client.get(f"scan:{scan_id}")
        if scan_data:
            scan_data['status'] = 'completed'
            scan_data['results'] = results
            scan_data['duration'] = total_duration
            scan_data['completed_at'] = '2024-01-01T00:00:00Z'  # Mock timestamp
            
            await redis_client.set(f"scan:{scan_id}", scan_data)
    
    async def _publish_scan_completion(
        self,
        scan_id: str,
        results: list,
        total_duration: int
    ):
        """Publish scan completion event."""
        event_data = {
            'type': 'scan_completed',
            'scan_id': scan_id,
            'status': 'completed',
            'results': results,
            'duration': total_duration,
        }
        
        await redis_client.publish("scan_events", event_data)


async def main():
    """Main entry point for the scanner worker."""
    worker = ScannerWorker()
    
    # Handle shutdown signals
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(worker.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Worker interrupted")
    finally:
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())