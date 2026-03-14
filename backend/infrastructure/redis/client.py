"""
Redis Client

This module provides Redis client functionality for caching, queuing, and session management.
"""
from typing import Optional, Dict, Any, List, Union
import asyncio
import json
import logging
from redis.asyncio import Redis
from redis.exceptions import RedisError

from config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis client for caching and queuing."""
    
    def __init__(self):
        self.redis: Optional[Redis] = None
        self.is_connected = False
        
    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis = Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                health_check_interval=30,
            )
            # Test connection
            await self.redis.ping()
            self.is_connected = True
            logger.info("Redis connection established successfully")
        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.is_connected = False
            raise
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            self.is_connected = False
            logger.info("Redis connection closed")
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis."""
        if not self.is_connected:
            await self.connect()
        
        try:
            return await self.redis.get(key)
        except RedisError as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: str, expire: Optional[int] = None):
        """Set value in Redis."""
        if not self.is_connected:
            await self.connect()
        
        try:
            if expire:
                await self.redis.setex(key, expire, value)
            else:
                await self.redis.set(key, value)
        except RedisError as e:
            logger.error(f"Redis SET error for key {key}: {e}")
    
    async def delete(self, key: str):
        """Delete key from Redis."""
        if not self.is_connected:
            await self.connect()
        
        try:
            await self.redis.delete(key)
        except RedisError as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        if not self.is_connected:
            await self.connect()
        
        try:
            return await self.redis.exists(key) == 1
        except RedisError as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False
    
    async def lpush(self, key: str, value: str):
        """Push value to left of list."""
        if not self.is_connected:
            await self.connect()
        
        try:
            await self.redis.lpush(key, value)
        except RedisError as e:
            logger.error(f"Redis LPUSH error for key {key}: {e}")
    
    async def rpop(self, key: str) -> Optional[str]:
        """Pop value from right of list."""
        if not self.is_connected:
            await self.connect()
        
        try:
            return await self.redis.rpop(key)
        except RedisError as e:
            logger.error(f"Redis RPOP error for key {key}: {e}")
            return None
    
    async def sadd(self, key: str, value: str):
        """Add value to set."""
        if not self.is_connected:
            await self.connect()
        
        try:
            await self.redis.sadd(key, value)
        except RedisError as e:
            logger.error(f"Redis SADD error for key {key}: {e}")
    
    async def smembers(self, key: str) -> List[str]:
        """Get all members of set."""
        if not self.is_connected:
            await self.connect()
        
        try:
            return await self.redis.smembers(key)
        except RedisError as e:
            logger.error(f"Redis SMEMBERS error for key {key}: {e}")
            return []
    
    async def publish(self, channel: str, message: str):
        """Publish message to channel."""
        if not self.is_connected:
            await self.connect()
        
        try:
            await self.redis.publish(channel, message)
        except RedisError as e:
            logger.error(f"Redis PUBLISH error for channel {channel}: {e}")
    
    async def subscribe(self, channel: str):
        """Subscribe to channel."""
        if not self.is_connected:
            await self.connect()
        
        try:
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(channel)
            return pubsub
        except RedisError as e:
            logger.error(f"Redis SUBSCRIBE error for channel {channel}: {e}")
            return None
    
    async def get_health(self) -> Dict[str, Any]:
        """Get Redis health status."""
        try:
            if not self.is_connected:
                await self.connect()
            
            info = await self.redis.info()
            return {
                "status": True,
                "type": "redis",
                "version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "connected": self.is_connected,
            }
        except RedisError as e:
            return {
                "status": False,
                "type": "redis",
                "error": str(e),
                "connected": self.is_connected,
            }
    
    async def flushdb(self):
        """Flush current database."""
        if not self.is_connected:
            await self.connect()
        
        try:
            await self.redis.flushdb()
        except RedisError as e:
            logger.error(f"Redis FLUSHDB error: {e}")


# Global Redis client instance
redis_client = RedisClient()


async def get_redis_health() -> Dict[str, Any]:
    """Get Redis health status."""
    return await redis_client.get_health()