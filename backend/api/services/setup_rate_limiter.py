"""
Setup Rate Limiter

This service handles rate limiting for setup operations to prevent brute force attacks
and ensure system security with multi-level protection.
"""
import json
from datetime import datetime, timedelta
from typing import Optional

from infrastructure.redis.client import redis_client


class SetupRateLimiter:
    """Rate limiter for setup operations with multi-level protection."""
    
    def __init__(self, minute_limit: int = 5, hour_limit: int = 20, ban_duration_minutes: int = 60):
        """
        Initialize SetupRateLimiter.
        
        Args:
            minute_limit: Maximum attempts per minute (default: 5)
            hour_limit: Maximum attempts per hour (default: 20)
            ban_duration_minutes: Ban duration in minutes after limit exceeded (default: 60)
        """
        self.minute_limit = minute_limit
        self.hour_limit = hour_limit
        self.ban_duration_minutes = ban_duration_minutes
        
        # Redis key prefixes
        self.minute_key_prefix = "setup:rate:minute:"
        self.hour_key_prefix = "setup:rate:hour:"
        self.ban_key_prefix = "setup:ban:"
    
    async def check_and_increment(self, ip: str) -> bool:
        """
        Check if IP is allowed and increment attempt counters.
        
        Args:
            ip: Client IP address
            
        Returns:
            True if allowed, False if rate limited
        """
        # Check if IP is currently banned
        is_banned = await self.is_banned(ip)
        print(f"[DEBUG rate_limiter] IP {ip}: is_banned={is_banned}")
        if is_banned:
            print(f"[DEBUG rate_limiter] IP {ip} is banned, returning False")
            return False
        
        # Check minute window
        minute_key = f"{self.minute_key_prefix}{ip}"
        minute_count = await self._get_counter(minute_key)
        print(f"[DEBUG rate_limiter] IP {ip}: minute_count={minute_count}, minute_limit={self.minute_limit}")
        
        if minute_count is not None and minute_count >= self.minute_limit:
            print(f"[DEBUG rate_limiter] IP {ip}: Minute limit exceeded, banning")
            await self.ban_ip(ip)
            return False
        
        # Check hour window
        hour_key = f"{self.hour_key_prefix}{ip}"
        hour_count = await self._get_counter(hour_key)
        print(f"[DEBUG rate_limiter] IP {ip}: hour_count={hour_count}, hour_limit={self.hour_limit}")
        
        if hour_count is not None and hour_count >= self.hour_limit:
            print(f"[DEBUG rate_limiter] IP {ip}: Hour limit exceeded, banning")
            await self.ban_ip(ip)
            return False
        
        # Increment counters
        await self._increment_counter(minute_key, 60)  # 1 minute TTL
        await self._increment_counter(hour_key, 3600)  # 1 hour TTL
        print(f"[DEBUG rate_limiter] IP {ip}: Counters incremented, returning True")
        
        return True
    
    async def ban_ip(self, ip: str):
        """
        Ban an IP address for the configured duration.
        
        Args:
            ip: IP address to ban
        """
        ban_key = f"{self.ban_key_prefix}{ip}"
        await self._set_counter(ban_key, 1, self.ban_duration_minutes * 60)
    
    async def unban_ip(self, ip: str):
        """
        Unban an IP address.
        
        Args:
            ip: IP address to unban
        """
        ban_key = f"{self.ban_key_prefix}{ip}"
        await self._delete_counter(ban_key)
    
    async def is_banned(self, ip: str) -> bool:
        """
        Check if an IP address is currently banned.
        
        Args:
            ip: IP address to check
            
        Returns:
            True if banned, False otherwise
        """
        ban_key = f"{self.ban_key_prefix}{ip}"
        return await self._get_counter(ban_key) is not None
    
    async def get_attempt_counts(self, ip: str) -> dict:
        """
        Get current attempt counts for an IP.
        
        Args:
            ip: IP address to check
            
        Returns:
            Dictionary with minute_count, hour_count, and is_banned
        """
        minute_key = f"{self.minute_key_prefix}{ip}"
        hour_key = f"{self.hour_key_prefix}{ip}"
        ban_key = f"{self.ban_key_prefix}{ip}"
        
        minute_count = await self._get_counter(minute_key) or 0
        hour_count = await self._get_counter(hour_key) or 0
        is_banned = await self._get_counter(ban_key) is not None
        
        return {
            "minute_count": minute_count,
            "hour_count": hour_count,
            "is_banned": is_banned,
            "minute_limit": self.minute_limit,
            "hour_limit": self.hour_limit,
            "ban_duration_minutes": self.ban_duration_minutes
        }
    
    async def reset_counters(self, ip: str):
        """
        Reset all counters for an IP address.
        
        Args:
            ip: IP address to reset
        """
        minute_key = f"{self.minute_key_prefix}{ip}"
        hour_key = f"{self.hour_key_prefix}{ip}"
        ban_key = f"{self.ban_key_prefix}{ip}"
        
        await self._delete_counter(minute_key)
        await self._delete_counter(hour_key)
        await self._delete_counter(ban_key)
    
    async def _get_counter(self, key: str) -> Optional[int]:
        """
        Get counter value from Redis.
        
        Args:
            key: Redis key
            
        Returns:
            Counter value or None if not found
        """
        try:
            value = await redis_client.get(key)
            return int(value) if value else None
        except (ValueError, TypeError):
            return None
    
    async def _increment_counter(self, key: str, ttl_seconds: int):
        """
        Increment counter in Redis with TTL.
        
        Args:
            key: Redis key
            ttl_seconds: Time to live in seconds
        """
        try:
            # Get current value
            current = await self._get_counter(key) or 0
            # Set new value with TTL
            await redis_client.set(key, str(current + 1), expire=ttl_seconds)
        except Exception:
            # If increment fails, just set to 1
            await redis_client.set(key, "1", expire=ttl_seconds)
    
    async def _set_counter(self, key: str, value: int, ttl_seconds: int):
        """
        Set counter value in Redis with TTL.
        
        Args:
            key: Redis key
            value: Counter value
            ttl_seconds: Time to live in seconds
        """
        await redis_client.set(key, str(value), expire=ttl_seconds)
    
    async def _delete_counter(self, key: str):
        """
        Delete counter from Redis.
        
        Args:
            key: Redis key
        """
        await redis_client.delete(key)
    
    def get_remaining_time(self, ip: str) -> dict:
        """
        Get remaining time until ban expires.
        
        Args:
            ip: IP address to check
            
        Returns:
            Dictionary with remaining_minutes and is_banned
        """
        ban_key = f"{self.ban_key_prefix}{ip}"
        ttl = redis_client.ttl(ban_key)
        
        if ttl > 0:
            remaining_minutes = max(0, (ttl + 59) // 60)  # Round up to minutes
            return {
                "is_banned": True,
                "remaining_minutes": remaining_minutes
            }
        else:
            return {
                "is_banned": False,
                "remaining_minutes": 0
            }