"""
Queue Service

This module provides Redis-based queue service for scan job management.
Supports strategies: fifo (default), priority, round_robin.
"""
import json
import logging
import os
from typing import Any, Dict, Optional
from datetime import datetime

from domain.entities.scan import Scan
from domain.datetime_serialization import isoformat_utc
from infrastructure.redis.client import redis_client
from config.settings import get_settings
from application.services.upload_service import resolve_upload_mount_path

logger = logging.getLogger(__name__)

# Default scanner image name (can be overridden via environment variable)
DEFAULT_SCANNER_IMAGE = os.getenv("SCANNER_IMAGE", "simpleseccheck-scanner:latest")


def _collect_metadata_default(config: Optional[dict]) -> bool:
    """If user did not set collect_metadata (missing or None), use admin default (usually False = no collection)."""
    if not config:
        return getattr(get_settings(), "COLLECT_METADATA_DEFAULT", False)
    v = config.get("collect_metadata")
    if v is not None:
        return bool(v)
    return getattr(get_settings(), "COLLECT_METADATA_DEFAULT", False)


class QueueService:
    """Redis-based queue service for scan jobs."""
    
    QUEUE_KEY = "scan_queue"
    QUEUE_PRIORITY_KEY = "scan_queue:priority"
    QUEUE_MESSAGE_TTL = 86400  # 24h for scan:{id} in priority mode
    
    def _get_strategy(self) -> str:
        s = getattr(get_settings(), "QUEUE_STRATEGY", "fifo") or "fifo"
        return s.lower() if s in ("fifo", "priority", "round_robin") else "fifo"
    
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
            
            # For uploaded_code, resolve upload_id to mount path (worker must have same path mounted)
            target_mount_path = None
            if scan.target_type == "uploaded_code":
                target_mount_path = resolve_upload_mount_path(scan.target_url)
                if not target_mount_path:
                    raise ValueError(
                        f"Upload not found or expired for target '{scan.target_url}'. "
                        "Please upload the ZIP again and start the scan with the new upload_id."
                    )
            else:
                target_mount_path = (scan.config or {}).get("target_mount_path")
            
            merged_final: Dict[str, Dict[str, Any]] = {}
            scanner_tool_overrides_json = "{}"
            try:
                from application.services.scanner_tool_overrides_service import (
                    build_merged_tool_overrides,
                    overrides_map_to_json,
                )
                from application.services.scan_profile_merge import merge_resolved_profile_into_overrides
                from application.services.scan_profile_resolver import resolve_scan_profile_from_manifests
                from infrastructure.container import get_scanner_repository

                merged = await build_merged_tool_overrides()
                cfg = scan.config or {}
                resolved = await resolve_scan_profile_from_manifests(
                    profile=cfg.get("scan_profile"),
                    profile_tuning=cfg.get("profile_tuning"),
                    scanner_repository=get_scanner_repository(),
                )
                merged_final = merge_resolved_profile_into_overrides(merged, resolved)
                scanner_tool_overrides_json = overrides_map_to_json(merged_final)
            except Exception as ex:
                logger.warning("scanner_tool_overrides merge skipped: %s", ex)

            from application.services.scan_enforcement import resolve_max_scan_wall_seconds_for_scan

            max_wall = await resolve_max_scan_wall_seconds_for_scan(scan, merged_final)

            queue_message = {
                "scan_id": scan_id,
                "id": scan_id,  # Worker may expect 'id'
                "job_id": scan_id,
                "job_type": "scan",
                "target": scan.target_url,
                "target_url": scan.target_url,
                "target_type": scan.target_type,
                "target_mount_path": target_mount_path,
                "scan_type": scan.scan_type.value,
                "scanners": scan.scanners,
                "config": scan.config,
                "image": scan.config.get("image", DEFAULT_SCANNER_IMAGE) if scan.config else DEFAULT_SCANNER_IMAGE,
                "finding_policy": scan.config.get("finding_policy") if scan.config else None,
                "collect_metadata": _collect_metadata_default(scan.config),
                "exclude_paths": scan.config.get("exclude_paths") if scan.config else None,
                "git_branch": scan.config.get("git_branch") if scan.config else None,
                "asset_volumes": asset_volumes,
                "user_id": scan.user_id,
                "project_id": scan.project_id,
                "scan_metadata": getattr(scan, "scan_metadata", None) or {},
                "scheduled_at": isoformat_utc(scan.scheduled_at),
                "enqueued_at": isoformat_utc(datetime.utcnow()),
                "scanner_tool_overrides_json": scanner_tool_overrides_json,
                "max_scan_wall_seconds": max_wall,
            }

            message_json = json.dumps(queue_message)
            strategy = self._get_strategy()
            
            try:
                if strategy == "priority":
                    # Store full message at scan:{id}, add scan_id to sorted set (lower score = earlier)
                    priority = getattr(scan, "priority", 0) or 0
                    created_ts = (scan.created_at or datetime.utcnow()).timestamp()
                    score = (1000 - priority) * 1e10 + created_ts
                    await redis_client.set(f"scan:{scan_id}", message_json, expire=self.QUEUE_MESSAGE_TTL)
                    await redis_client.zadd(self.QUEUE_PRIORITY_KEY, {scan_id: score})
                    logger.info(f"Enqueued scan {scan.id} to priority queue (priority={priority})")
                else:
                    # fifo or round_robin: same list (worker chooses by strategy)
                    queue_length = await redis_client.lpush(self.QUEUE_KEY, message_json)
                    logger.info(f"Enqueued scan {scan.id} to queue (strategy={strategy}, length={queue_length})")
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
        """Get current queue length (list or priority set)."""
        try:
            if not redis_client.is_connected:
                await redis_client.connect()
            strategy = self._get_strategy()
            if strategy == "priority":
                return await redis_client.zcard(self.QUEUE_PRIORITY_KEY)
            return await redis_client.redis.llen(self.QUEUE_KEY)
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
        Remove a specific scan from the Redis queue (list or priority set).
        """
        try:
            if not redis_client.is_connected:
                await redis_client.connect()
            
            removed = False
            strategy = self._get_strategy()
            if strategy == "priority":
                n = await redis_client.zrem(self.QUEUE_PRIORITY_KEY, scan_id)
                if n:
                    removed = True
                    await redis_client.delete(f"scan:{scan_id}")
                    logger.info(f"Removed scan {scan_id} from priority queue")
            else:
                items = await redis_client.lrange(self.QUEUE_KEY, 0, -1)
                for item in items:
                    try:
                        message = json.loads(item)
                        if message.get("scan_id") == scan_id:
                            await redis_client.lrem(self.QUEUE_KEY, 1, item)
                            removed = True
                            logger.info(f"Removed scan {scan_id} from Redis queue")
                            break
                    except json.JSONDecodeError:
                        continue
            
            if not removed:
                logger.warning(f"Scan {scan_id} not found in Redis queue")
            return removed
            
        except Exception as e:
            logger.error(f"Failed to remove scan {scan_id} from queue: {e}")
            return False

    async def signal_worker_cancel(self, scan_id: str) -> None:
        """Signal the worker to stop the running container for this scan_id. No-op if worker unreachable."""
        try:
            import httpx
            worker_url = os.getenv("WORKER_API_URL", "http://worker:8081")
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(f"{worker_url}/api/jobs/cancel/{scan_id}")
                if response.status_code == 200:
                    data = response.json()
                    if data.get("stopped"):
                        logger.info(f"Worker stopped container for scan {scan_id}")
                else:
                    logger.warning(
                        f"Worker cancel returned {response.status_code} for scan {scan_id}: {response.text}"
                    )
        except Exception as e:
            logger.warning(f"Could not signal worker to cancel scan {scan_id}: {e}")

    async def cancel_scan(self, scan_id: str) -> bool:
        """
        Cancel a scan - removes from queue if pending, signals worker to stop container if running.
        """
        try:
            await self.remove_scan_from_queue(scan_id)
            await self.signal_worker_cancel(scan_id)
            logger.info(f"Cancelled scan {scan_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel scan {scan_id}: {e}")
            return False