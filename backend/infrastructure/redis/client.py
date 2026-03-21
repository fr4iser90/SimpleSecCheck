"""
Redis Client

This module provides Redis client functionality for caching, queuing, and session management.
"""
from typing import Any, Optional, Dict, List, Tuple, Union, cast
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

    async def scan_keys(self, pattern: str, limit: int = 500) -> List[str]:
        """Return up to `limit` keys matching glob pattern (SCAN, production-safe)."""
        if not self.is_connected:
            await self.connect()
        out: List[str] = []
        try:
            async for key in self.redis.scan_iter(match=pattern, count=100):
                out.append(key)
                if len(out) >= limit:
                    break
            return out
        except RedisError as e:
            logger.error(f"Redis SCAN error pattern={pattern}: {e}")
            return []
    
    async def lpush(self, key: str, value: str) -> int:
        """Push value to left of list.
        
        Returns:
            Length of list after push, or raises exception on error
        """
        if not self.is_connected:
            await self.connect()
        
        try:
            result = await self.redis.lpush(key, value)
            logger.debug(f"Redis LPUSH successful for key {key}, new length: {result}")
            return result
        except RedisError as e:
            logger.error(f"Redis LPUSH error for key {key}: {e}", exc_info=True)
            raise
    
    async def rpop(self, key: str) -> Optional[str]:
        """Pop value from right of list."""
        if not self.is_connected:
            await self.connect()
        
        try:
            return await self.redis.rpop(key)
        except RedisError as e:
            logger.error(f"Redis RPOP error for key {key}: {e}")
            return None

    async def brpop(self, key: str, timeout: int = 1) -> Optional[tuple]:
        """Blocking pop from right of list. Returns (key, value) or None on timeout."""
        if not self.is_connected:
            await self.connect()
        try:
            result = await self.redis.brpop(key, timeout=timeout)
            return result
        except RedisError as e:
            logger.error(f"Redis BRPOP error for key {key}: {e}")
            return None

    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        """Get list slice. end=-1 means to the end."""
        if not self.is_connected:
            await self.connect()
        try:
            return await self.redis.lrange(key, start, end)
        except RedisError as e:
            logger.error(f"Redis LRANGE error for key {key}: {e}")
            return []

    async def lrem(self, key: str, count: int, value: str) -> int:
        """Remove first `count` occurrences of value from list. Returns number removed."""
        if not self.is_connected:
            await self.connect()
        try:
            return await self.redis.lrem(key, count, value)
        except RedisError as e:
            logger.error(f"Redis LREM error for key {key}: {e}")
            return 0

    async def zadd(self, key: str, mapping: Dict[str, float], nx: bool = False) -> int:
        """Add members to sorted set. mapping: {member: score}. Returns number of new elements."""
        if not self.is_connected:
            await self.connect()
        try:
            if nx:
                return await self.redis.zadd(key, mapping, nx=True)
            return await self.redis.zadd(key, mapping)
        except RedisError as e:
            logger.error(f"Redis ZADD error for key {key}: {e}")
            raise

    async def zrange(self, key: str, start: int, end: int) -> List[str]:
        """Get sorted set range by index (ascending). end=-1 means to the end."""
        if not self.is_connected:
            await self.connect()
        try:
            return await self.redis.zrange(key, start, end)
        except RedisError as e:
            logger.error(f"Redis ZRANGE error for key {key}: {e}")
            return []

    async def zrem(self, key: str, *members: str) -> int:
        """Remove members from sorted set. Returns number removed."""
        if not self.is_connected:
            await self.connect()
        try:
            return await self.redis.zrem(key, *members)
        except RedisError as e:
            logger.error(f"Redis ZREM error for key {key}: {e}")
            return 0

    async def zcard(self, key: str) -> int:
        """Get sorted set cardinality."""
        if not self.is_connected:
            await self.connect()
        try:
            return await self.redis.zcard(key)
        except RedisError as e:
            logger.error(f"Redis ZCARD error for key {key}: {e}")
            return 0
    
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
    
    async def publish(self, channel: str, message: Union[str, Dict[str, Any]]):
        """Publish message to channel (JSON-encode dicts)."""
        if not self.is_connected:
            await self.connect()
        payload: str
        if isinstance(message, dict):
            payload = json.dumps(message, separators=(",", ":"))
        else:
            payload = cast(str, message)
        try:
            await self.redis.publish(channel, payload)
        except RedisError as e:
            logger.error(f"Redis PUBLISH error for channel {channel}: {e}")
    
    async def subscribe(self, channel: str) -> Optional[Tuple[Any, Redis]]:
        """
        Subscribe to a channel for long-lived ``pubsub.listen()``.

        Uses a **dedicated** Redis client with ``socket_timeout=None``. The shared
        pool client uses ``socket_timeout=5``, which breaks blocking pubsub reads
        during idle periods (redis.exceptions.TimeoutError).
        """
        try:
            pub_redis = Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=None,
                health_check_interval=30,
            )
            await pub_redis.ping()
            pubsub = pub_redis.pubsub()
            await pubsub.subscribe(channel)
            return (pubsub, pub_redis)
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