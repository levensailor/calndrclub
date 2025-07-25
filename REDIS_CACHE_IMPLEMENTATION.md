# Redis Cache Implementation for Calndr

## Overview

This document describes the Redis caching implementation added to the Calndr backend to improve performance for frequently requested data, particularly for the iOS app.

## Architecture

### Redis Service (`backend/services/redis_service.py`)
- **Connection Management**: Automatic connection handling with reconnection logic
- **Error Handling**: Graceful degradation when Redis is unavailable
- **Key Management**: Consistent key generation with app prefix (`calndr:`)
- **TTL Support**: Configurable time-to-live for different data types

### Cache Middleware (`backend/core/cache_middleware.py`)
- **Automatic Caching**: Transparent caching for configured endpoints
- **Cache Invalidation**: Smart invalidation on data modifications
- **User-Specific Caching**: Per-user and per-family cache isolation

## Cached Endpoints

### 1. Events (`/api/v1/events/`)
- **Cache Duration**: 15 minutes (configurable via `CACHE_TTL_EVENTS`)
- **Cache Key**: `events:family:{family_id}:{start_date}:{end_date}`
- **Invalidation**: On event creation, update, or deletion
- **Benefit**: Significant performance improvement for calendar views

### 2. Weather (`/api/v1/weather/`)
- **Forecast Cache Duration**: 1 hour (configurable via `CACHE_TTL_WEATHER_FORECAST`)
- **Historic Cache Duration**: 3 days (configurable via `CACHE_TTL_WEATHER_HISTORIC`)
- **Cache Key**: `weather:{type}:{lat}:{lon}:{start}:{end}`
- **Benefit**: Reduces external API calls to Open-Meteo

### 3. User Profile (`/api/v1/user/profile`)
- **Cache Duration**: 30 minutes (configurable via `CACHE_TTL_USER_PROFILE`)
- **Cache Key**: `user:{user_id}:profile`
- **Invalidation**: On profile updates

### 4. Family Data (`/api/v1/family/`)
- **Cache Duration**: 30 minutes (configurable via `CACHE_TTL_FAMILY_DATA`)
- **Cache Key**: `family:{family_id}:data`
- **Invalidation**: On family data modifications

## Configuration

### Environment Variables

```bash
# Redis Connection
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=  # Optional
REDIS_DB=0
REDIS_MAX_CONNECTIONS=10
REDIS_SOCKET_TIMEOUT=5

# Cache TTL Settings (in seconds)
CACHE_TTL_WEATHER_FORECAST=3600    # 1 hour
CACHE_TTL_WEATHER_HISTORIC=259200  # 3 days
CACHE_TTL_EVENTS=900               # 15 minutes
CACHE_TTL_USER_PROFILE=1800        # 30 minutes
CACHE_TTL_FAMILY_DATA=1800         # 30 minutes
```

### Redis Configuration

The deployment script configures Redis with:
- **Memory Limit**: 128MB with LRU eviction
- **Persistence**: Disabled (cache-only mode)
- **Security**: Bound to localhost only
- **Performance**: Optimized for low-latency operations

## Cache Operations

### Cache Management Functions

```python
# Get cached data
cached_data = await get_cached_data(cache_key)

# Set cached data with TTL
await set_cached_data(cache_key, data, ttl_seconds)

# Delete specific cache entry
await delete_cached_data(cache_key)

# Clear all cache for a family
await clear_family_cache(family_id)

# Clear all cache for a user
await clear_user_cache(user_id)
```

### Cache Key Patterns

- Events: `calndr:events:family:{family_id}:{start_date}:{end_date}`
- Weather: `calndr:weather:{type}:{latitude}:{longitude}:{start}:{end}`
- User Profile: `calndr:user:{user_id}:profile`
- Family Data: `calndr:family:{family_id}:data`

## Monitoring

### Cache Status Endpoint

Access cache statistics at: `https://calndr.club/cache-status`

Response includes:
- Connection status
- Memory usage
- Hit/miss ratios
- Configuration settings

### Redis Monitoring Commands

```bash
# Check Redis service status
sudo systemctl status redis

# Monitor Redis operations in real-time
redis-cli monitor

# View memory usage
redis-cli info memory

# View all keys (development only)
redis-cli keys "calndr:*"

# Clear all cache (development only)
redis-cli flushdb
```

## Performance Benefits

### Expected Improvements

1. **Events Endpoint**: 70-90% faster response times for cached requests
2. **Weather Endpoint**: Eliminates external API calls for repeated requests
3. **User Profile**: Faster authentication and profile loading
4. **Database Load**: Reduced by 40-60% for frequently accessed data

### iOS App Benefits

- **Calendar Loading**: Near-instant calendar views for cached months
- **Weather Display**: Immediate weather information without API delays
- **Offline Resilience**: Cached data available during brief connectivity issues

## Cache Invalidation Strategy

### Automatic Invalidation

- **Events**: Cleared on any event modification for the affected family
- **User Profile**: Cleared on profile updates
- **Family Data**: Cleared on family setting changes

### Manual Invalidation

Use the Redis service functions to clear specific cache patterns:

```python
# Clear all events cache for a family
await redis_service.clear_family_cache(family_id)

# Clear all user-related cache
await redis_service.clear_user_cache(user_id)

# Clear specific cache patterns
await redis_service.delete_pattern("events:family:123:*")
```

## Deployment

### Requirements

- Redis server installed and configured
- Updated Python dependencies (`redis>=4.5.0`, `aioredis>=2.0.1`)
- Environment variables configured

### Deployment Steps

1. Run the updated deployment script: `./deploy.sh`
2. Redis will be automatically installed and configured
3. Application will connect to Redis on startup
4. Monitor cache status at `/cache-status` endpoint

### Rollback Plan

If issues occur:
1. Redis can be disabled by stopping the service: `sudo systemctl stop redis`
2. Application will continue to work without caching (graceful degradation)
3. No data loss - cache is supplementary to database operations

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   - Check service status: `sudo systemctl status redis`
   - Verify Redis is listening: `redis-cli ping`
   - Check firewall settings

2. **High Memory Usage**
   - Monitor with: `redis-cli info memory`
   - Adjust maxmemory setting in `/etc/redis.conf`
   - Consider reducing TTL values

3. **Cache Misses**
   - Check cache-status endpoint for hit ratios
   - Verify cache keys are being generated correctly
   - Monitor Redis logs: `sudo tail -f /var/log/redis/redis.log`

### Performance Tuning

- Adjust TTL values based on data change frequency
- Monitor hit ratios and adjust cache strategies
- Consider increasing Redis memory limit for high-traffic scenarios
- Use Redis slow log to identify performance bottlenecks

## Security Considerations

- Redis is bound to localhost only (127.0.0.1)
- No external network access to Redis
- Consider adding Redis password for additional security
- Regular security updates for Redis package

## Future Enhancements

- **Cache Warming**: Pre-populate cache with frequently accessed data
- **Cache Compression**: Compress large JSON responses
- **Distributed Caching**: Scale to multiple Redis instances if needed
- **Cache Analytics**: Enhanced monitoring and alerting 