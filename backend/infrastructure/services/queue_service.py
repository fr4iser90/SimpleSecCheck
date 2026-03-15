"""
Queue Service

This module provides Redis-based queue service for scan job management.
"""
import json
import logging
from typing import Optional
from datetime import datetime

from domain.entities.scan import Scan
from infrastructure.redis.client import redis_client

logger = logging.getLogger(__name__)


class QueueService:
    """Redis-based queue service for scan jobs."""
    
    QUEUE_KEY = "scan_queue"
    QUEUE_PRIORITY_KEY = "scan_queue:priority"
    
    async def enqueue_scan(self, scan: Scan) -> bool:
        """Enqueue a scan for processing by the worker."""
        try:
            if not redis_client.is_connected:
                await redis_client.connect()
            
            # Create queue message - format must match worker expectations
            # Worker expects: scan_id, job_type, target, image, results_dir, logs_dir, scan_type, etc.
            scan_id = scan.id
            results_dir = f"/app/results/{scan_id}"
            logs_dir = f"/app/logs/{scan_id}"
            
            queue_message = {
                "scan_id": scan_id,
                "job_id": scan_id,  # Use scan_id as job_id if not separate
                "job_type": "scan",  # Required by worker
                "target": scan.target_url,  # Worker expects 'target', not 'target_url'
                "target_url": scan.target_url,  # Keep for compatibility
                "target_type": scan.target_type,
                "target_mount_path": scan.config.get("target_mount_path") if scan.config else None,
                "scan_type": scan.scan_type.value,
                "scanners": scan.scanners,
                "config": scan.config,
                "image": scan.config.get("image", "simpleseccheck/scanner:latest") if scan.config else "simpleseccheck/scanner:latest",
                "results_dir": results_dir,
                "logs_dir": logs_dir,
                "finding_policy": scan.config.get("finding_policy") if scan.config else None,
                "collect_metadata": scan.config.get("collect_metadata", True) if scan.config else True,
                "exclude_paths": scan.config.get("exclude_paths") if scan.config else None,
                "user_id": scan.user_id,
                "project_id": scan.project_id,
                "scheduled_at": scan.scheduled_at.isoformat() if scan.scheduled_at else None,
                "enqueued_at": datetime.utcnow().isoformat(),
            }
            
            # Serialize message
            message_json = json.dumps(queue_message)
            
            # Add to queue (FIFO - left push, right pop)
            try:
                queue_length = await redis_client.lpush(self.QUEUE_KEY, message_json)
                logger.info(f"Enqueued scan {scan.id} to queue (queue length: {queue_length})")
                return True
            except Exception as e:
                logger.error(f"Failed to enqueue scan {scan.id} to queue: {e}", exc_info=True)
                raise
            
        except Exception as e:
            logger.error(f"Failed to enqueue scan {scan.id}: {e}")
            raise
    
    async def dequeue_scan(self) -> Optional[dict]:
        """Dequeue a scan from the queue (worker picks it up)."""
        try:
            if not redis_client.is_connected:
                await redis_client.connect()
            
            # Pop from right (FIFO)
            message_json = await redis_client.rpop(self.QUEUE_KEY)
            
            if message_json:
                message = json.loads(message_json)
                logger.info(f"Dequeued scan {message.get('scan_id')} from queue")
                return message
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to dequeue scan: {e}")
            raise
    
    async def get_queue_length(self) -> int:
        """Get current queue length."""
        try:
            if not redis_client.is_connected:
                await redis_client.connect()
            
            length = await redis_client.redis.llen(self.QUEUE_KEY)
            return length
            
        except Exception as e:
            logger.error(f"Failed to get queue length: {e}")
            return 0
    
    async def peek_queue(self, count: int = 10) -> list:
        """Peek at the next N items in the queue without removing them."""
        try:
            if not redis_client.is_connected:
                await redis_client.connect()
            
            # Use LRANGE to peek at items
            items = await redis_client.redis.lrange(self.QUEUE_KEY, 0, count - 1)
            
            messages = []
            for item in items:
                try:
                    messages.append(json.loads(item))
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse queue item: {item}")
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to peek queue: {e}")
            return []
    
    async def clear_queue(self) -> bool:
        """Clear all items from the queue."""
        try:
            if not redis_client.is_connected:
                await redis_client.connect()
            
            await redis_client.delete(self.QUEUE_KEY)
            logger.info("Cleared scan queue")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear queue: {e}")
            return False
