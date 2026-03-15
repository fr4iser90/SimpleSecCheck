"""
Queue adapter for the worker domain.

Provides queue operations for job queuing and management.
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime


class QueueAdapter:
    """Adapter for queue operations."""
    
    def __init__(self, queue_type: str = "redis", connection_string: Optional[str] = None):
        """Initialize the queue adapter.
        
        Args:
            queue_type: Type of queue (redis, memory, etc.)
            connection_string: Connection string for the queue
        """
        self.queue_type = queue_type
        self.connection_string = connection_string
        self.logger = logging.getLogger(__name__)
        # Don't suppress logs - we need to see queue operations
        
        if queue_type == "redis":
            self._init_redis()
        else:
            self._init_memory()
    
    def _init_redis(self) -> None:
        """Initialize Redis connection."""
        if not self.connection_string:
            raise ValueError("Redis connection string is required. Set REDIS_URL or QUEUE_CONNECTION environment variable.")
        
        try:
            import redis.asyncio as redis
            self.logger.info(f"Initializing Redis connection to: {self.connection_string}")
            self.redis_client = redis.from_url(self.connection_string, decode_responses=True)
            self.logger.info("Redis client created successfully")
        except ImportError:
            raise ImportError("Redis library not available. Install redis package.")
        except Exception as e:
            self.logger.error(f"Failed to initialize Redis: {e}")
            raise
    
    def _init_memory(self) -> None:
        """Initialize in-memory queue."""
        self.queue = []
    
    async def push_job(self, job_data: Dict[str, Any]) -> bool:
        """Push a job to the queue.
        
        Args:
            job_data: Job data to push
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.queue_type == "redis":
                try:
                    # Serialize job data to JSON
                    job_json = json.dumps(job_data)
                    await self.redis_client.lpush("scan_queue", job_json)
                    self.logger.info(f"Pushed job to queue: {job_data.get('scan_id')}")
                    return True
                except json.JSONEncodeError as e:
                    self.logger.error(f"Failed to serialize job data to JSON: {e}", exc_info=True)
                    return False
                except Exception as e:
                    self.logger.error(f"Error pushing job to Redis queue: {e}", exc_info=True)
                    return False
            else:
                self.queue.append(job_data)
                self.logger.info(f"Pushed job to memory queue: {job_data.get('scan_id')}")
                return True
            
        except Exception as e:
            self.logger.error(f"Unexpected error pushing job to queue: {e}", exc_info=True)
            return False
    
    async def pop_job(self) -> Optional[Dict[str, Any]]:
        """Pop a job from the queue.
        
        Returns:
            Job data if available, None otherwise
        """
        try:
            if self.queue_type == "redis":
                # Check connection first
                try:
                    await self.redis_client.ping()
                except Exception as e:
                    self.logger.error(f"Redis connection error: {e}", exc_info=True)
                    return None
                
                # Check queue length with error handling
                queue_length = 0
                try:
                    queue_length = await self.redis_client.llen("scan_queue")
                    if queue_length > 0:
                        self.logger.info(f"Queue has {queue_length} job(s), attempting to pop...")
                    else:
                        self.logger.debug(f"Queue is empty (length: {queue_length})")
                except Exception as e:
                    self.logger.error(f"Error getting queue length: {e}", exc_info=True)
                    return None
                
                # Try to pop job from queue
                try:
                    result = await self.redis_client.brpop("scan_queue", timeout=1)
                    if result:
                        self.logger.info(f"Popped job from queue: key={result[0]}")
                        try:
                            # Parse JSON with error handling
                            job_data = json.loads(result[1])
                            self.logger.info(f"Parsed job data for scan_id: {job_data.get('scan_id')}")
                            return job_data
                        except json.JSONDecodeError as e:
                            self.logger.error(f"Failed to parse job JSON: {e}. Raw data: {result[1][:200]}", exc_info=True)
                            return None
                        except Exception as e:
                            self.logger.error(f"Unexpected error parsing job data: {e}", exc_info=True)
                            return None
                    else:
                        if queue_length > 0:
                            self.logger.warning(f"Queue has {queue_length} jobs but brpop returned None - possible connection issue")
                        # Don't log every timeout, only if queue has items
                except Exception as e:
                    self.logger.error(f"Error during brpop operation: {e}", exc_info=True)
                    return None
            else:
                if self.queue:
                    return self.queue.pop(0)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Unexpected error in pop_job: {e}", exc_info=True)
            return None
    
    async def get_queue_length(self) -> int:
        """Get queue length.
        
        Returns:
            Queue length
        """
        try:
            if self.queue_type == "redis":
                try:
                    length = await self.redis_client.llen("scan_queue")
                    self.logger.debug(f"Queue length: {length}")
                    return length
                except Exception as e:
                    self.logger.error(f"Error getting queue length from Redis: {e}", exc_info=True)
                    return 0
            else:
                return len(self.queue)
            
        except Exception as e:
            self.logger.error(f"Unexpected error getting queue length: {e}", exc_info=True)
            return 0
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status from queue.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job status if available, None otherwise
        """
        try:
            if self.queue_type == "redis":
                # Check if job is in progress (in a separate set)
                in_progress = await self.redis_client.sismember("jobs_in_progress", job_id)
                if in_progress:
                    return {"status": "running", "job_id": job_id}
                
                # Check if job is completed (in a separate set)
                completed = await self.redis_client.sismember("jobs_completed", job_id)
                if completed:
                    return {"status": "completed", "job_id": job_id}
                
                # Check if job is failed (in a separate set)
                failed = await self.redis_client.sismember("jobs_failed", job_id)
                if failed:
                    return {"status": "failed", "job_id": job_id}
                
                # Check if job is in queue
                queue_length = await self.get_queue_length()
                for i in range(queue_length):
                    try:
                        job_data = await self.redis_client.lindex("scan_queue", i)
                        if job_data:
                            try:
                                job = json.loads(job_data)
                                if job.get("job_id") == job_id:
                                    return {"status": "queued", "job_id": job_id, "position": i + 1}
                            except json.JSONDecodeError as e:
                                self.logger.warning(f"Failed to parse job JSON at index {i}: {e}")
                                continue
                            except Exception as e:
                                self.logger.warning(f"Error parsing job at index {i}: {e}")
                                continue
                    except Exception as e:
                        self.logger.warning(f"Error getting job at index {i}: {e}")
                        continue
                
            else:
                # Check memory queue
                for i, job in enumerate(self.queue):
                    if job.get("job_id") == job_id:
                        return {"status": "queued", "job_id": job_id, "position": i + 1}
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting job status: {e}")
            return None
    
    async def set_job_status(self, job_id: str, status: str) -> bool:
        """Set job status.
        
        Args:
            job_id: Job ID
            status: Job status
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.queue_type == "redis":
                # Remove from all status sets
                await self.redis_client.srem("jobs_in_progress", job_id)
                await self.redis_client.srem("jobs_completed", job_id)
                await self.redis_client.srem("jobs_failed", job_id)
                
                # Add to appropriate status set
                if status == "running":
                    await self.redis_client.sadd("jobs_in_progress", job_id)
                elif status == "completed":
                    await self.redis_client.sadd("jobs_completed", job_id)
                elif status == "failed":
                    await self.redis_client.sadd("jobs_failed", job_id)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting job status: {e}")
            return False
    
    async def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """Clean up old jobs from queue.
        
        Args:
            max_age_hours: Maximum age in hours
            
        Returns:
            Number of jobs cleaned up
        """
        try:
            cleaned_count = 0
            
            if self.queue_type == "redis":
                # Clean up old jobs from queue
                cutoff_time = datetime.utcnow().timestamp() - (max_age_hours * 3600)
                
                # This would require more complex logic with Redis
                # For now, just return 0
                pass
            else:
                # Clean up old jobs from memory queue
                current_time = datetime.utcnow()
                self.queue = [
                    job for job in self.queue
                    if (current_time - datetime.fromisoformat(job.get("created_at", current_time.isoformat()))).total_seconds() < (max_age_hours * 3600)
                ]
                cleaned_count = len(self.queue)
            
            self.logger.info(f"Cleaned up {cleaned_count} old jobs")
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old jobs: {e}")
            return 0