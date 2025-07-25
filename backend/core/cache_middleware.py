import json
import hashlib
from typing import Dict, Optional, Callable, Any
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from core.config import settings
from core.logging import logger
from services.redis_service import redis_service

class CacheMiddleware:
    """
    Middleware to automatically cache API responses based on configured rules.
    """
    
    def __init__(self, app):
        self.app = app
        # Configure which endpoints to cache and their TTL
        self.cache_config = {
            # Events endpoints - cache for 15 minutes
            "/api/v1/events/": {
                "ttl": settings.CACHE_TTL_EVENTS,
                "methods": ["GET"],
                "cache_per_user": True
            },
            # Weather endpoints - cache for 1 hour (forecast) or 3 days (historic)
            "/api/v1/weather/": {
                "ttl": settings.CACHE_TTL_WEATHER_FORECAST,
                "methods": ["GET"],
                "cache_per_user": False  # Weather is location-based, not user-specific
            },
            # User profile endpoints - cache for 30 minutes
            "/api/v1/user/profile": {
                "ttl": settings.CACHE_TTL_USER_PROFILE,
                "methods": ["GET"],
                "cache_per_user": True
            },
            # Family data endpoints - cache for 30 minutes
            "/api/v1/family/": {
                "ttl": settings.CACHE_TTL_FAMILY_DATA,
                "methods": ["GET"],
                "cache_per_user": True
            }
        }
        
        # Endpoints that should invalidate cache when modified
        self.cache_invalidation_config = {
            "/api/v1/events/": ["family_events"],
            "/api/v1/user/profile": ["user_profile"],
            "/api/v1/family/": ["family_data"]
        }
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Process request through cache middleware."""
        
        # Check if this endpoint should be cached
        cache_config = self._get_cache_config(request)
        
        if cache_config and request.method == "GET":
            # Try to get cached response
            cached_response = await self._get_cached_response(request, cache_config)
            if cached_response:
                return cached_response
        
        # Process the request
        response = await call_next(request)
        
        # Cache the response if it's successful and cacheable
        if cache_config and request.method == "GET" and response.status_code == 200:
            await self._cache_response(request, response, cache_config)
        
        # Invalidate cache if this is a modifying operation
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            await self._invalidate_cache(request)
        
        return response
    
    def _get_cache_config(self, request: Request) -> Optional[Dict]:
        """Get cache configuration for the request path."""
        path = request.url.path
        
        # Check for exact matches first
        if path in self.cache_config:
            return self.cache_config[path]
        
        # Check for partial matches (endpoints with parameters)
        for config_path, config in self.cache_config.items():
            if path.startswith(config_path):
                return config
        
        return None
    
    async def _get_cached_response(self, request: Request, cache_config: Dict) -> Optional[Response]:
        """Get cached response if available."""
        try:
            cache_key = await self._generate_cache_key(request, cache_config)
            cached_data = await redis_service.get(cache_key)
            
            if cached_data:
                logger.debug(f"Cache hit for {request.url.path}")
                return JSONResponse(content=cached_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached response: {e}")
            return None
    
    async def _cache_response(self, request: Request, response: Response, cache_config: Dict) -> None:
        """Cache the response."""
        try:
            # Only cache JSON responses
            if not hasattr(response, 'body'):
                return
            
            # Get response body
            response_body = response.body
            if isinstance(response_body, bytes):
                response_body = response_body.decode('utf-8')
            
            try:
                response_data = json.loads(response_body)
            except json.JSONDecodeError:
                # Skip caching non-JSON responses
                return
            
            cache_key = await self._generate_cache_key(request, cache_config)
            ttl = cache_config.get("ttl", 900)  # Default 15 minutes
            
            await redis_service.set(cache_key, response_data, ttl)
            logger.debug(f"Cached response for {request.url.path} (TTL: {ttl}s)")
            
        except Exception as e:
            logger.error(f"Error caching response: {e}")
    
    async def _generate_cache_key(self, request: Request, cache_config: Dict) -> str:
        """Generate cache key for the request."""
        # Base key components
        key_parts = [
            "api_cache",
            request.url.path,
            str(request.query_params) if request.query_params else "no_params"
        ]
        
        # Add user-specific component if needed
        if cache_config.get("cache_per_user", False):
            # Try to get user ID from request context
            user_id = getattr(request.state, 'user_id', None)
            if hasattr(request, 'state') and hasattr(request.state, 'current_user'):
                user_id = request.state.current_user.get('id')
            
            if user_id:
                key_parts.append(f"user:{user_id}")
        
        # Create hash of key parts for consistent length
        key_string = ":".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    async def _invalidate_cache(self, request: Request) -> None:
        """Invalidate cache for modifying operations."""
        try:
            path = request.url.path
            
            # Find invalidation patterns for this endpoint
            for config_path, cache_types in self.cache_invalidation_config.items():
                if path.startswith(config_path):
                    # Get user context for targeted invalidation
                    user_id = getattr(request.state, 'user_id', None)
                    family_id = getattr(request.state, 'family_id', None)
                    
                    if hasattr(request, 'state') and hasattr(request.state, 'current_user'):
                        user_data = request.state.current_user
                        user_id = user_data.get('id')
                        family_id = user_data.get('family_id')
                    
                    # Invalidate based on cache types
                    for cache_type in cache_types:
                        if cache_type == "family_events" and family_id:
                            pattern = f"events:family:{family_id}:*"
                            await redis_service.delete_pattern(pattern)
                            logger.info(f"Invalidated family events cache for family {family_id}")
                        
                        elif cache_type == "user_profile" and user_id:
                            pattern = f"user:{user_id}:*"
                            await redis_service.delete_pattern(pattern)
                            logger.info(f"Invalidated user profile cache for user {user_id}")
                        
                        elif cache_type == "family_data" and family_id:
                            pattern = f"family:{family_id}:*"
                            await redis_service.delete_pattern(pattern)
                            logger.info(f"Invalidated family data cache for family {family_id}")
        
        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")

# Decorator for manually adding cache control to specific endpoints
def cache_response(ttl: int = 900, cache_per_user: bool = True):
    """
    Decorator to add caching to specific endpoint functions.
    
    Args:
        ttl: Time to live in seconds
        cache_per_user: Whether to cache per user or globally
    """
    def decorator(func):
        func._cache_ttl = ttl
        func._cache_per_user = cache_per_user
        return func
    return decorator

def invalidate_cache(*cache_patterns: str):
    """
    Decorator to invalidate specific cache patterns after endpoint execution.
    
    Args:
        cache_patterns: Pattern strings to invalidate (e.g., "family:{family_id}:*")
    """
    def decorator(func):
        func._invalidate_patterns = cache_patterns
        return func
    return decorator 