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

@router.post("/", response_model=CustodyResponse)
async def create_custody(custody_data: CustodyRecord, current_user = Depends(get_current_user)):
    """
    Creates a new custody record for a specific date.
    Returns 409 Conflict if a record already exists for the date.
    """
    logger.info(f"📝 Received custody CREATE request: {custody_data.model_dump_json(indent=2)}")
    
    family_id = current_user['family_id']
    actor_id = current_user['id']
    
    try:
        # Check if a record already exists for this date
        existing_record_query = custody.select().where(
            (custody.c.family_id == family_id) &
            (custody.c.date == custody_data.date)
        )
        existing_record = await database.fetch_one(existing_record_query)
        
        if existing_record:
            logger.warning(f"❌ Custody record already exists for date {custody_data.date}")
            raise HTTPException(
                status_code=409, 
                detail=f"Custody record already exists for date {custody_data.date}. Use PUT to update."
            )
        
        # Determine handoff_day value
        handoff_day_value = custody_data.handoff_day
        if handoff_day_value is None and custody_data.handoff_time is not None:
            handoff_day_value = True
        elif handoff_day_value is None:
            # Default logic: check if previous day has different custodian
            previous_date = custody_data.date - timedelta(days=1)
            previous_record = await database.fetch_one(
                custody.select().where(
                    (custody.c.family_id == family_id) &
                    (custody.c.date == previous_date)
                )
            )
            if previous_record and previous_record['custodian_id'] != custody_data.custodian_id:
                handoff_day_value = True
                logger.info(f"🔄 Detected custodian change from previous day, setting handoff_day=True")
            else:
                handoff_day_value = False

        logger.info(f"⚡ Creating new custody record for {custody_data.date}")
        
        # Insert new record
        insert_query = custody.insert().values(
            family_id=family_id,
            date=custody_data.date,
            custodian_id=custody_data.custodian_id,
            actor_id=actor_id,
            handoff_day=handoff_day_value,
            handoff_time=datetime.strptime(custody_data.handoff_time, '%H:%M').time() if custody_data.handoff_time else None,
            handoff_location=custody_data.handoff_location,
            created_at=datetime.now()
        )
        record_id = await database.execute(insert_query)
            
        # Invalidate cache for this month with verification
        cache_key = f"custody_opt:family:{family_id}:{custody_data.date.year}:{custody_data.date.month:02d}"
        cache_existed = await redis_service.exists(cache_key)
        cache_deleted = await redis_service.delete(cache_key)
        
        # Also invalidate handoff-only cache
        handoff_cache_key = f"handoff_only:family:{family_id}:{custody_data.date.year}:{custody_data.date.month:02d}"
        handoff_cache_existed = await redis_service.exists(handoff_cache_key)
        handoff_cache_deleted = await redis_service.delete(handoff_cache_key)
        
        # Verify cache invalidation
        if cache_existed and not cache_deleted:
            logger.warning(f"⚠️ Failed to invalidate main custody cache: {cache_key}")
        if handoff_cache_existed and not handoff_cache_deleted:
            logger.warning(f"⚠️ Failed to invalidate handoff cache: {handoff_cache_key}")
        
        # Additional pattern-based cache invalidation for extra safety
        pattern = f"custody*:family:{family_id}:*"
        pattern_deleted = await redis_service.delete_pattern(pattern)
        
        logger.info(f"🗑️ Cache invalidation for family {family_id} month {custody_data.date.year}/{custody_data.date.month}: "
                   f"main_cache={'deleted' if cache_deleted else 'failed'} "
                   f"handoff_cache={'deleted' if handoff_cache_deleted else 'failed'} "
                   f"pattern_deleted={pattern_deleted}")
            
        # Get custodian name for response
        custodian_user = await database.fetch_one(users.select().where(users.c.id == custody_data.custodian_id))
        custodian_name = custodian_user['first_name'] if custodian_user else "Unknown"

        logger.info(f"✅ Successfully created custody record for {custody_data.date}")

        return CustodyResponse(
            id=record_id,
            event_date=str(custody_data.date),
            content=custodian_name,
            custodian_id=uuid_to_string(custody_data.custodian_id),
            handoff_day=handoff_day_value,
            handoff_time=custody_data.handoff_time,
            handoff_location=custody_data.handoff_location
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating custody record: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error while creating custody: {e}")

@router.put("/date/{custody_date}", response_model=CustodyResponse)
async def update_custody_by_date(custody_date: date, custody_data: CustodyRecord, current_user = Depends(get_current_user)):
    """
    Updates an existing custody record for a specific date.
    Returns 404 if no record exists for the date.
    """
    logger.info(f"🔄 Received custody UPDATE request for {custody_date}: {custody_data.model_dump_json(indent=2)}")
    
    family_id = current_user['family_id']
    actor_id = current_user['id']
    
    try:
        # Check if record exists for this date
        existing_record_query = custody.select().where(
            (custody.c.family_id == family_id) &
            (custody.c.date == custody_date)
        )
        existing_record = await database.fetch_one(existing_record_query)
        
        if not existing_record:
            logger.warning(f"❌ No custody record found for date {custody_date} in family {family_id}")
            raise HTTPException(status_code=404, detail=f"No custody record found for date {custody_date}")
        
        # Determine handoff_day value
        handoff_day_value = custody_data.handoff_day
        if handoff_day_value is None and custody_data.handoff_time is not None:
            handoff_day_value = True
        elif handoff_day_value is None:
            handoff_day_value = False
        
        logger.info(f"⚡ Updating custody record {existing_record['id']} for date {custody_date}")
        
        # Update the existing record
        update_query = custody.update().where(custody.c.id == existing_record['id']).values(
            custodian_id=custody_data.custodian_id,
            actor_id=actor_id,
            handoff_day=handoff_day_value,
            handoff_time=datetime.strptime(custody_data.handoff_time, '%H:%M').time() if custody_data.handoff_time else None,
            handoff_location=custody_data.handoff_location
        )
        await database.execute(update_query)
        
        # Invalidate cache for this month with verification
        cache_key = f"custody_opt:family:{family_id}:{custody_date.year}:{custody_date.month:02d}"
        cache_existed = await redis_service.exists(cache_key)
        cache_deleted = await redis_service.delete(cache_key)
        
        # Also invalidate handoff-only cache
        handoff_cache_key = f"handoff_only:family:{family_id}:{custody_date.year}:{custody_date.month:02d}"
        handoff_cache_existed = await redis_service.exists(handoff_cache_key)
        handoff_cache_deleted = await redis_service.delete(handoff_cache_key)
        
        # Verify cache invalidation
        if cache_existed and not cache_deleted:
            logger.warning(f"⚠️ Failed to invalidate main custody cache: {cache_key}")
        if handoff_cache_existed and not handoff_cache_deleted:
            logger.warning(f"⚠️ Failed to invalidate handoff cache: {handoff_cache_key}")
        
        # Additional pattern-based cache invalidation for extra safety
        pattern = f"custody*:family:{family_id}:*"
        pattern_deleted = await redis_service.delete_pattern(pattern)
        
        logger.info(f"🗑️ Cache invalidation for family {family_id} month {custody_date.year}/{custody_date.month}: "
                   f"main_cache={'deleted' if cache_deleted else 'failed'} "
                   f"handoff_cache={'deleted' if handoff_cache_deleted else 'failed'} "
                   f"pattern_deleted={pattern_deleted}")
        
        # Get updated record to return
        updated_record_query = custody.select().where(custody.c.id == existing_record['id'])
        updated_record = await database.fetch_one(updated_record_query)
        
        # Get custodian name
        custodian_query = users.select().where(users.c.id == updated_record['custodian_id'])
        custodian = await database.fetch_one(custodian_query)
        
        logger.info(f"✅ Successfully updated custody record for {custody_date}")
        
        return CustodyResponse(
            id=updated_record['id'],
            event_date=str(updated_record['date']),
            content=custodian['first_name'] if custodian else "Unknown",
            custodian_id=uuid_to_string(updated_record['custodian_id']),
            handoff_day=updated_record['handoff_day'],
            handoff_time=updated_record['handoff_time'].strftime('%H:%M') if updated_record['handoff_time'] else None,
            handoff_location=updated_record['handoff_location']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating custody record for {custody_date}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error while updating custody: {e}")

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
        WHERE c.family_id = :family_id 
        AND c.date >= :start_date 
        AND c.date <= :end_date
        ORDER BY c.date ASC
        """
        
        start_time = datetime.now()
        db_records = await database.fetch_all(query, {
            'family_id': family_id,
            'start_date': start_date,
            'end_date': end_date
        })
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
        WHERE c.family_id = :family_id 
        AND c.date >= :start_date 
        AND c.date <= :end_date
        AND c.handoff_day = true
        AND c.handoff_time IS NOT NULL
        ORDER BY c.date ASC
        """
        
        start_time = datetime.now()
        db_records = await database.fetch_all(query, {
            'family_id': family_id,
            'start_date': start_date,
            'end_date': end_date
        })
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
        WHERE family_id = :family_id
        """
        
        db_stats = await database.fetch_one(db_stats_query, {'family_id': family_id})
        
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