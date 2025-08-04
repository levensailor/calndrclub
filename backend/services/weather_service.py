import hashlib
from typing import Optional, Dict
from core.config import settings
from core.logging import logger
from services.redis_service import redis_service

def get_cache_key(latitude: float, longitude: float, start_date: str, end_date: str, endpoint_type: str) -> str:
    """Generate a unique cache key for weather data."""
    key_string = f"weather:{endpoint_type}:{latitude}:{longitude}:{start_date}:{end_date}"
    return hashlib.md5(key_string.encode()).hexdigest()

async def get_cached_weather(cache_key: str) -> Optional[Dict]:
    """Get cached weather data from Redis."""
    try:
        cached_data = await redis_service.get(cache_key)
        if cached_data:
            logger.debug(f"Weather cache hit for key: {cache_key}")
            return cached_data
        else:
            logger.debug(f"Weather cache miss for key: {cache_key}")
            return None
    except Exception as e:
        logger.error(f"Error getting cached weather data: {e}")
        return None

async def cache_weather_data(cache_key: str, data: Dict, endpoint_type: str = "forecast"):
    """Cache weather data in Redis with appropriate TTL."""
    try:
        # Determine TTL based on endpoint type
        if "historic" in endpoint_type:
            ttl = settings.CACHE_TTL_WEATHER_HISTORIC
        else:
            ttl = settings.CACHE_TTL_WEATHER_FORECAST
        
        success = await redis_service.set(cache_key, data, ttl)
        if success:
            logger.debug(f"Cached weather data for key: {cache_key} (TTL: {ttl}s)")
        else:
            logger.warning(f"Failed to cache weather data for key: {cache_key}")
    except Exception as e:
        logger.error(f"Error caching weather data: {e}")
