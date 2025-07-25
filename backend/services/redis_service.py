import json
import time
import hashlib
import asyncio
from typing import Optional, Dict, Any, Union
from datetime import datetime, timedelta
import aioredis
from aioredis import Redis

from core.config import settings
from core.logging import logger

class RedisService:
    """Redis caching service with connection management and error handling."""
    
    def __init__(self):
        self.redis_pool: Optional[Redis] = None
        self._connection_retries = 3
        self._reconnect_delay = 1  # seconds
    
    async def connect(self) -> None:
        """Initialize Redis connection pool."""
        try:
            # Build Redis URL
            auth_string = ""
            if settings.REDIS_PASSWORD:
                auth_string = f":{settings.REDIS_PASSWORD}@"
            
            redis_url = f"redis://{auth_string}{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
            
            self.redis_pool = aioredis.from_url(
                redis_url,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                retry_on_timeout=True,
                decode_responses=True
            )
            
            # Test connection
            await self.redis_pool.ping()
            logger.info(f"Connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_pool = None
            # Don't raise exception - allow app to continue without cache
    
    async def disconnect(self) -> None:
        """Close Redis connection pool."""
        if self.redis_pool:
            await self.redis_pool.close()
            logger.info("Disconnected from Redis")
    
    async def _ensure_connection(self) -> bool:
        """Ensure Redis connection is available, attempt reconnection if needed."""
        if not self.redis_pool:
            await self.connect()
            return self.redis_pool is not None
        
        try:
            await self.redis_pool.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis connection lost, attempting reconnection: {e}")
            await self.connect()
            return self.redis_pool is not None
    
    def _generate_cache_key(self, key_parts: Union[str, list]) -> str:
        """Generate a consistent cache key from string or list of parts."""
        if isinstance(key_parts, str):
            key_string = key_parts
        else:
            key_string = ":".join(str(part) for part in key_parts)
        
        # Add app prefix to avoid conflicts
        return f"calndr:{key_string}"
    
    async def get(self, key: Union[str, list]) -> Optional[Dict]:
        """Get cached data by key."""
        if not await self._ensure_connection():
            logger.warning("Redis not available, returning None for cache get")
            return None
        
        try:
            cache_key = self._generate_cache_key(key)
            # Reduced timeout to prevent client disconnections
            cached_data = await asyncio.wait_for(
                self.redis_pool.get(cache_key), 
                timeout=2.0  # Reduced from 5.0 to 2.0 seconds
            )
            
            if cached_data:
                data = json.loads(cached_data)
                logger.debug(f"Cache hit for key: {cache_key}")
                return data
            else:
                logger.debug(f"Cache miss for key: {cache_key}")
                return None
                
        except asyncio.TimeoutError:
            logger.warning(f"Redis get operation timed out for key {key} - returning None")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for cached data with key {key}: {e}")
            # Clean up corrupted cache entry
            await self.delete(key)
            return None
        except Exception as e:
            logger.error(f"Error getting cached data for key {key}: {e}")
            return None
    
    async def set(self, key: Union[str, list], data: Dict, ttl: Optional[int] = None) -> bool:
        """Set cached data with optional TTL."""
        if not await self._ensure_connection():
            logger.warning("Redis not available, skipping cache set")
            return False
        
        try:
            cache_key = self._generate_cache_key(key)
            serialized_data = json.dumps(data, default=str)
            
            # Reduced timeout to prevent blocking
            if ttl:
                await asyncio.wait_for(
                    self.redis_pool.setex(cache_key, ttl, serialized_data),
                    timeout=2.0  # Reduced from 5.0 to 2.0 seconds
                )
            else:
                await asyncio.wait_for(
                    self.redis_pool.set(cache_key, serialized_data),
                    timeout=2.0  # Reduced from 5.0 to 2.0 seconds
                )
            
            logger.debug(f"Cached data for key: {cache_key} (TTL: {ttl}s)")
            return True
        
        except asyncio.TimeoutError:
            logger.warning(f"Redis set operation timed out for key {key} - skipping cache")
            return False
        except Exception as e:
            logger.error(f"Error setting cached data for key {key}: {e}")
            return False
    
    async def delete(self, key: Union[str, list]) -> bool:
        """Delete cached data by key."""
        if not await self._ensure_connection():
            logger.warning("Redis not available, skipping cache delete")
            return False
        
        try:
            cache_key = self._generate_cache_key(key)
            result = await self.redis_pool.delete(cache_key)
            logger.debug(f"Deleted cache key: {cache_key}")
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error deleting cached data for key {key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        if not await self._ensure_connection():
            logger.warning("Redis not available, skipping pattern delete")
            return 0
        
        try:
            cache_pattern = self._generate_cache_key(pattern)
            # Reduced timeout for keys lookup
            keys = await asyncio.wait_for(
                self.redis_pool.keys(cache_pattern),
                timeout=2.0  # Reduced from 5.0 to 2.0 seconds
            )
            
            if not keys:
                return 0
            
            # Delete keys in smaller batches to prevent timeouts
            batch_size = 25  # Reduced from 50 to 25 for faster processing
            total_deleted = 0
            
            for i in range(0, len(keys), batch_size):
                batch_keys = keys[i:i + batch_size]
                # Shorter timeout for each batch deletion
                try:
                    deleted_count = await asyncio.wait_for(
                        self.redis_pool.delete(*batch_keys),
                        timeout=1.5  # Reduced from 3.0 to 1.5 seconds
                    )
                    total_deleted += deleted_count
                    logger.debug(f"Deleted batch of {deleted_count} keys (batch {i//batch_size + 1})")
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout deleting batch {i//batch_size + 1}, continuing with next batch")
                    continue
            
            logger.debug(f"Deleted {total_deleted} keys matching pattern: {cache_pattern}")
            return total_deleted
        
        except asyncio.TimeoutError:
            logger.warning(f"Redis delete pattern operation timed out for pattern {pattern}")
            return 0
        except Exception as e:
            logger.error(f"Error deleting keys with pattern {pattern}: {e}")
            return 0
    
    async def exists(self, key: Union[str, list]) -> bool:
        """Check if a key exists in cache."""
        if not await self._ensure_connection():
            return False
        
        try:
            cache_key = self._generate_cache_key(key)
            result = await self.redis_pool.exists(cache_key)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error checking key existence for {key}: {e}")
            return False
    
    async def get_ttl(self, key: Union[str, list]) -> Optional[int]:
        """Get TTL for a key."""
        if not await self._ensure_connection():
            return None
        
        try:
            cache_key = self._generate_cache_key(key)
            ttl = await self.redis_pool.ttl(cache_key)
            return ttl if ttl > 0 else None
            
        except Exception as e:
            logger.error(f"Error getting TTL for key {key}: {e}")
            return None
    
    async def clear_family_cache(self, family_id: int) -> int:
        """Clear all cached data for a specific family."""
        try:
            total_deleted = 0
            
            # Clear events cache patterns
            events_patterns = [
                f"events:family:{family_id}:*",
                f"api_cache:*/api/v1/events/*family_id*{family_id}*",
                f"family:{family_id}:*"
            ]
            
            for pattern in events_patterns:
                deleted = await self.delete_pattern(pattern)
                total_deleted += deleted
                logger.debug(f"Deleted {deleted} keys for pattern: {pattern}")
            
            logger.info(f"Cleared {total_deleted} cache entries for family {family_id}")
            return total_deleted
            
        except Exception as e:
            logger.error(f"Error clearing family cache for {family_id}: {e}")
            return 0
    
    async def clear_user_cache(self, user_id: int) -> int:
        """Clear all cached data for a specific user."""
        pattern = f"user:{user_id}:*"
        deleted = await self.delete_pattern(pattern)
        logger.info(f"Cleared {deleted} cache entries for user {user_id}")
        return deleted
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not await self._ensure_connection():
            return {"status": "disconnected"}
        
        try:
            info = await self.redis_pool.info()
            return {
                "status": "connected",
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "hit_rate": round(
                    info.get("keyspace_hits", 0) / 
                    max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1) * 100, 2
                ) if info.get("keyspace_hits", 0) or info.get("keyspace_misses", 0) else 0
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"status": "error", "error": str(e)}

# Global Redis service instance
redis_service = RedisService()

# Convenience functions for common cache operations
async def get_cached_data(key: Union[str, list]) -> Optional[Dict]:
    """Get cached data."""
    return await redis_service.get(key)

async def set_cached_data(key: Union[str, list], data: Dict, ttl: Optional[int] = None) -> bool:
    """Set cached data."""
    return await redis_service.set(key, data, ttl)

async def delete_cached_data(key: Union[str, list]) -> bool:
    """Delete cached data."""
    return await redis_service.delete(key)

async def clear_family_cache(family_id: int) -> int:
    """Clear all cached data for a family."""
    return await redis_service.clear_family_cache(family_id)

async def clear_user_cache(user_id: int) -> int:
    """Clear all cached data for a user."""
    return await redis_service.clear_user_cache(user_id)

# Cache key generators for different data types
def weather_cache_key(latitude: float, longitude: float, start_date: str, end_date: str, endpoint_type: str) -> str:
    """Generate cache key for weather data."""
    key_string = f"weather:{endpoint_type}:{latitude}:{longitude}:{start_date}:{end_date}"
    return hashlib.md5(key_string.encode()).hexdigest()

def events_cache_key(family_id: int, start_date: str, end_date: str) -> str:
    """Generate cache key for events data."""
    return f"events:family:{family_id}:{start_date}:{end_date}"

def user_profile_cache_key(user_id: int) -> str:
    """Generate cache key for user profile data."""
    return f"user:{user_id}:profile"

def family_data_cache_key(family_id: int) -> str:
    """Generate cache key for family data."""
    return f"family:{family_id}:data" 