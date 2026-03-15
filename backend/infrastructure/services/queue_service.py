"""
Queue Service

This module provides Redis-based queue service for scan job management.
"""
import json
import logging
import os
from typing import Optional
from datetime import datetime

from domain.entities.scan import Scan
from infrastructure.redis.client import redis_client

logger = logging.getLogger(__name__)

# Default scanner image name (can be overridden via environment variable)
DEFAULT_SCANNER_IMAGE = os.getenv("SCANNER_IMAGE", "simpleseccheck-scanner:local")


class QueueService:
    """Redis-based queue service for scan jobs."""
    
    QUEUE_KEY = "scan_queue"
    QUEUE_PRIORITY_KEY = "scan_queue:priority"
    
    async def enqueue_scan(self, scan: Scan) -> bool:
        """Enqueue a scan for processing by the worker."""
        try:
            if not redis_client.is_connected:
                await redis_client.connect()
            
            # Create queue message - ENTERPRISE: Only send metadata, NO PATHS!
            # Worker determines paths from its own environment variables (generic, portable)
            # This follows separation of concerns: Backend doesn't know about Worker's filesystem layout
            scan_id = scan.id
            
            # Collect asset volumes from scanner manifests (if available)
            # Plugins define their required volumes in manifest.yaml
            asset_volumes = []
            try:
                import httpx
                worker_url = os.getenv("WORKER_API_URL", "http://worker:8081")
                async with httpx.AsyncClient(timeout=5.0) as client:
                    try:
                        # Get scanner assets from worker API
                        response = await client.get(f"{worker_url}/api/scanners/assets")
                        if response.status_code == 200:
                            assets_data = response.json().get("assets", [])
                            # Filter assets for selected scanners and extract mount info
                            selected_scanners = set(scan.scanners or [])
                            for asset_item in assets_data:
                                scanner_name = asset_item.get("scanner", "").lower()
                                if scanner_name in [s.lower() for s in selected_scanners]:
                                    asset = asset_item.get("asset", {})
                                    mount = asset.get("mount", {})
                                    if mount.get("host_subpath") and mount.get("container_path"):
                                        asset_volumes.append({
                                            "host_subpath": mount["host_subpath"],
                                            "container_path": mount["container_path"]
                                        })
                    except Exception as e:
                        logger.debug(f"Could not fetch scanner assets for volumes: {e}")
            except Exception as e:
                logger.debug(f"Failed to collect asset volumes: {e}")
            
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
                "image": scan.config.get("image", DEFAULT_SCANNER_IMAGE) if scan.config else DEFAULT_SCANNER_IMAGE,
                # NO results_dir, NO logs_dir - Worker reads from own environment variables!
                "finding_policy": scan.config.get("finding_policy") if scan.config else None,
                "collect_metadata": scan.config.get("collect_metadata", True) if scan.config else True,
                "exclude_paths": scan.config.get("exclude_paths") if scan.config else None,
                "git_branch": scan.config.get("git_branch") if scan.config else None,
                "asset_volumes": asset_volumes,  # Asset volumes from scanner manifests
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
    
    async def remove_scan_from_queue(self, scan_id: str) -> bool:
        """
        Remove a specific scan from the Redis queue.
        
        Args:
            scan_id: ID of the scan to remove
            
        Returns:
            True if scan was found and removed, False otherwise
        """
        try:
            if not redis_client.is_connected:
                await redis_client.connect()
            
            # Get all items from queue
            items = await redis_client.redis.lrange(self.QUEUE_KEY, 0, -1)
            
            # Find and remove the scan
            removed = False
            for item in items:
                try:
                    message = json.loads(item)
                    if message.get("scan_id") == scan_id:
                        # Remove this item from queue
                        await redis_client.redis.lrem(self.QUEUE_KEY, 1, item)
                        logger.info(f"Removed scan {scan_id} from Redis queue")
                        removed = True
                        break
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse queue item: {item}")
                    continue
            
            if not removed:
                logger.warning(f"Scan {scan_id} not found in Redis queue")
            
            return removed
            
        except Exception as e:
            logger.error(f"Failed to remove scan {scan_id} from queue: {e}")
            return False
    
    async def cancel_scan(self, scan_id: str) -> bool:
        """
        Cancel a scan - removes from queue if pending, signals worker if running.
        
        Args:
            scan_id: ID of the scan to cancel
            
        Returns:
            True if cancellation was successful
        """
        try:
            # Remove from queue if pending
            await self.remove_scan_from_queue(scan_id)
            
            # TODO: Signal worker to stop if running
            # This would require worker API call or Redis pub/sub
            
            logger.info(f"Cancelled scan {scan_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel scan {scan_id}: {e}")
            return False