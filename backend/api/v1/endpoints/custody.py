import uuid
from typing import List
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
import traceback

from core.database import database
from core.security import get_current_user, uuid_to_string
from core.logging import logger
from core.config import settings
from db.models import custody, users
from schemas.custody import CustodyRecord, CustodyResponse
from services.notification_service import send_custody_change_notification
from services.redis_service import redis_service

router = APIRouter()

@router.get("/{year}/{month}", response_model=List[CustodyResponse])
async def get_custody_records_optimized(year: int, month: int, current_user = Depends(get_current_user)):
    """
    OPTIMIZED: Returns custody records for the specified month with improved performance.
    
    Performance improvements:
    - Single JOIN query instead of 2 separate queries
    - Optimized date calculation 
    - Better caching strategy
    - Reduced data processing overhead
    """
    try:
        family_id = current_user['family_id']
        
        # Optimized date calculation - simpler and faster
        from calendar import monthrange
        start_date = date(year, month, 1)
        _, last_day = monthrange(year, month)
        end_date = date(year, month, last_day)
        
        # Check cache first with improved key structure
        custody_cache_key = f"custody_opt:family:{family_id}:{year}:{month:02d}"
        cached_custody = await redis_service.get(custody_cache_key)
        
        if cached_custody is not None:
            logger.info(f"✅ Cache HIT: Returning {len(cached_custody)} custody records for {year}/{month}")
            return cached_custody
        
        logger.info(f"🔍 Cache MISS: Querying database for custody records {year}/{month}")
        
        # OPTIMIZED: Single JOIN query instead of 2 separate queries
        # This reduces database round trips and improves performance significantly
        query = """
        SELECT 
            c.id,
            c.date,
            c.custodian_id,
            c.handoff_day,
            c.handoff_time,
            c.handoff_location,
            u.first_name as custodian_name
        FROM custody c
        JOIN users u ON c.custodian_id = u.id
        WHERE c.family_id = $1 
        AND c.date >= $2 
        AND c.date <= $3
        ORDER BY c.date ASC
        """
        
        start_time = datetime.now()
        db_records = await database.fetch_all(query, family_id, start_date, end_date)
        query_duration = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"⚡ Database query completed in {query_duration:.3f}s ({len(db_records)} records)")
        
        # Convert records to CustodyResponse format with minimal processing
        custody_responses = []
        for record in db_records:
            custody_responses.append(CustodyResponse(
                id=record['id'],
                event_date=str(record['date']),
                content=record['custodian_name'],  # Already fetched in JOIN
                custodian_id=uuid_to_string(record['custodian_id']),
                handoff_day=record['handoff_day'],
                handoff_time=record['handoff_time'].strftime('%H:%M') if record['handoff_time'] else None,
                handoff_location=record['handoff_location']
            ))
        
        # Cache with optimized TTL based on data freshness
        # Shorter TTL for current month, longer for past months
        current_month = datetime.now().date().replace(day=1)
        query_month = start_date
        
        if query_month >= current_month:
            # Current or future month - shorter cache (30 minutes)
            cache_ttl = 1800
        else:
            # Past month - longer cache (4 hours) 
            cache_ttl = 14400
        
        # Cache the custody records (convert to dict for JSON serialization)
        custody_responses_dict = [resp.model_dump() for resp in custody_responses]
        await redis_service.set(custody_cache_key, custody_responses_dict, cache_ttl)
        
        total_duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ Optimized custody query completed in {total_duration:.3f}s (cached for {cache_ttl}s)")
        
        return custody_responses
        
    except Exception as e:
        logger.error(f"❌ Error fetching custody records: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/handoff-only/{year}/{month}", response_model=List[CustodyResponse])  
async def get_handoff_times_only(year: int, month: int, current_user = Depends(get_current_user)):
    """
    SPECIALIZED: Returns only custody records with handoff times for maximum performance.
    Use this endpoint specifically for handoff times to reduce data transfer.
    """
    try:
        family_id = current_user['family_id']
        
        # Optimized date calculation
        from calendar import monthrange
        start_date = date(year, month, 1)
        _, last_day = monthrange(year, month)
        end_date = date(year, month, last_day)
        
        # Specialized cache key for handoff-only data
        handoff_cache_key = f"handoff_only:family:{family_id}:{year}:{month:02d}"
        cached_handoffs = await redis_service.get(handoff_cache_key)
        
        if cached_handoffs is not None:
            logger.info(f"✅ Handoff Cache HIT: {len(cached_handoffs)} records for {year}/{month}")
            return cached_handoffs
        
        # HIGHLY OPTIMIZED: Query only handoff days with times
        query = """
        SELECT 
            c.id,
            c.date,
            c.custodian_id,
            c.handoff_day,
            c.handoff_time,
            c.handoff_location,
            u.first_name as custodian_name
        FROM custody c
        JOIN users u ON c.custodian_id = u.id
        WHERE c.family_id = $1 
        AND c.date >= $2 
        AND c.date <= $3
        AND c.handoff_day = true
        AND c.handoff_time IS NOT NULL
        ORDER BY c.date ASC
        """
        
        start_time = datetime.now()
        db_records = await database.fetch_all(query, family_id, start_date, end_date)
        query_duration = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"⚡ Handoff-only query completed in {query_duration:.3f}s ({len(db_records)} records)")
        
        # Convert to response format
        handoff_responses = []
        for record in db_records:
            handoff_responses.append(CustodyResponse(
                id=record['id'],
                event_date=str(record['date']),
                content=f"Handoff to {record['custodian_name']}",
                custodian_id=uuid_to_string(record['custodian_id']),
                handoff_day=True,  # Always true for this endpoint
                handoff_time=record['handoff_time'].strftime('%H:%M'),
                handoff_location=record['handoff_location']
            ))
        
        # Cache handoff data (longer TTL since handoffs change less frequently)
        handoff_responses_dict = [resp.model_dump() for resp in handoff_responses]
        await redis_service.set(handoff_cache_key, handoff_responses_dict, 3600)  # 1 hour
        
        total_duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ Handoff-only query completed in {total_duration:.3f}s")
        
        return handoff_responses
        
    except Exception as e:
        logger.error(f"❌ Error fetching handoff times: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Performance monitoring endpoint
@router.get("/performance/stats")
async def get_performance_stats(current_user = Depends(get_current_user)):
    """
    Returns performance statistics for custody queries.
    Useful for monitoring and debugging performance issues.
    """
    try:
        family_id = current_user['family_id']
        
        # Get cache statistics
        cache_stats = await redis_service.get_cache_stats()
        
        # Get database statistics for custody table
        db_stats_query = """
        SELECT 
            COUNT(*) as total_records,
            COUNT(CASE WHEN handoff_day = true THEN 1 END) as handoff_records,
            MIN(date) as earliest_date,
            MAX(date) as latest_date
        FROM custody 
        WHERE family_id = $1
        """
        
        db_stats = await database.fetch_one(db_stats_query, family_id)
        
        return {
            "family_id": str(family_id),
            "database_stats": {
                "total_custody_records": db_stats['total_records'],
                "handoff_records": db_stats['handoff_records'],
                "date_range": {
                    "earliest": str(db_stats['earliest_date']) if db_stats['earliest_date'] else None,
                    "latest": str(db_stats['latest_date']) if db_stats['latest_date'] else None
                }
            },
            "cache_stats": cache_stats,
            "optimization_tips": [
                "Use /handoff-only endpoint for handoff times only",
                "Cache is automatically optimized based on month (current vs past)",
                "Database indexes should be deployed for optimal performance"
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting performance stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") 