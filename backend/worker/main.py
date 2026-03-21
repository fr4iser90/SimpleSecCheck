"""
Scanner Worker

This module contains the scanner worker that processes scan jobs from the queue.
Supports queue strategies: fifo (default), priority, round_robin.
"""
import asyncio
import json
import logging
import os
import signal
import sys
import time
from typing import Dict, Any, Optional

from infrastructure.redis.client import redis_client
from infrastructure.docker_runner import docker_runner
from infrastructure.logging_config import setup_logging
from config.settings import get_settings

settings = get_settings()
QUEUE_KEY = "scan_queue"
QUEUE_PRIORITY_KEY = "scan_queue:priority"
LAST_RUN_KEY_PREFIX = "scan_queue:last_run:"

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


def _get_strategy() -> str:
    s = getattr(get_settings(), "QUEUE_STRATEGY", "fifo") or "fifo"
    return s.lower() if s in ("fifo", "priority", "round_robin") else "fifo"


class ScannerWorker:
    """Scanner worker for processing scan jobs."""
    
    def __init__(self):
        self.running = False
        self.shutdown_event = asyncio.Event()
        
    async def start(self):
        """Start the scanner worker."""
        logger.info("Starting scanner worker (queue strategy: %s)", _get_strategy())
        
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
                scan_data = await self._get_next_job()
                if scan_data:
                    scan_id = scan_data.get("scan_id") or scan_data.get("id")
                    logger.info("Processing scan job: %s", scan_id)
                    await self._execute_scan(scan_data)
                    if _get_strategy() == "round_robin" and scan_data.get("user_id"):
                        await redis_client.set(
                            f"{LAST_RUN_KEY_PREFIX}{scan_data['user_id']}", str(time.time()), expire=86400
                        )
                    session_id = (scan_data.get("scan_metadata") or {}).get("session_id")
                    if _get_strategy() == "round_robin" and session_id and not scan_data.get("user_id"):
                        await redis_client.set(
                            f"{LAST_RUN_KEY_PREFIX}session:{session_id}", str(time.time()), expire=86400
                        )
                else:
                    await asyncio.sleep(0.5)
            except Exception as e:
                logger.error("Error processing job: %s", e)
                await asyncio.sleep(1)
    
    async def _get_next_job(self) -> Optional[Dict[str, Any]]:
        """Get next job according to queue strategy. Returns parsed scan_data dict or None."""
        strategy = _get_strategy()
        if strategy == "priority":
            ids = await redis_client.zrange(QUEUE_PRIORITY_KEY, 0, 0)
            if not ids:
                return None
            scan_id = ids[0]
            await redis_client.zrem(QUEUE_PRIORITY_KEY, scan_id)
            raw = await redis_client.get(f"scan:{scan_id}")
            if not raw:
                return None
            try:
                return json.loads(raw) if isinstance(raw, str) else raw
            except json.JSONDecodeError:
                return None
        if strategy == "round_robin":
            items = await redis_client.lrange(QUEUE_KEY, 0, -1)
            if not items:
                return None
            messages = []
            for item in items:
                try:
                    messages.append(json.loads(item))
                except json.JSONDecodeError:
                    continue
            if not messages:
                return None
            # Pick user/session with smallest last_run (oldest last run)
            best_msg = None
            best_ts = float("inf")
            for msg in messages:
                user_key = msg.get("user_id") or ("session:" + str((msg.get("scan_metadata") or {}).get("session_id", "")))
                if not user_key or user_key == "session:":
                    user_key = "guest"
                last_run = await redis_client.get(f"{LAST_RUN_KEY_PREFIX}{user_key}")
                ts = float(last_run) if last_run else 0.0
                if ts < best_ts:
                    best_ts = ts
                    best_msg = msg
            if not best_msg:
                best_msg = messages[0]
            # Remove this exact message from the list
            for item in items:
                try:
                    m = json.loads(item)
                    if (m.get("scan_id") or m.get("id")) == (best_msg.get("scan_id") or best_msg.get("id")):
                        await redis_client.lrem(QUEUE_KEY, 1, item)
                        break
                except json.JSONDecodeError:
                    continue
            return best_msg
        # fifo: brpop (right = oldest)
        job_data = await redis_client.brpop(QUEUE_KEY, timeout=1)
        if not job_data:
            return None
        value = job_data[1]
        if isinstance(value, str) and value.strip().startswith("{"):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        # Fallback: value is scan_id, load from Redis
        raw = await redis_client.get(f"scan:{value}")
        if not raw:
            return None
        try:
            return json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError:
            return None
    
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
        user_id = None
        if scan_data and isinstance(scan_data, dict):
            user_id = scan_data.get("user_id")
        event_data = {
            'type': 'scan_completed',
            'scan_id': scan_id,
            'status': 'completed',
            'results': results,
            'duration': total_duration,
            'user_id': user_id,
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