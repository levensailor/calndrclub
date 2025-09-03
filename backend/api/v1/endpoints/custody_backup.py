import uuid
from typing import List
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
import traceback

from backend.core.database import database
from backend.core.security import get_current_user, uuid_to_string
from backend.core.logging import logger
from backend.core.config import settings
from backend.db.models import custody, users
from backend.schemas.custody import CustodyRecord, CustodyResponse
from backend.services.notification_service import send_custody_change_notification
from backend.services.redis_service import redis_service

router = APIRouter()

@router.get("/{year}/{month}", response_model=List[CustodyResponse])
async def get_custody_records(year: int, month: int, current_user = Depends(get_current_user)):
    """
    Returns custody records for the specified month.
    """
    try:
        family_id = current_user['family_id']
        # Calculate start and end dates for the month
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year, 1, 1) + timedelta(days=31)
            end_date = end_date.replace(day=1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        # Check cache first for custody records
        custody_cache_key = f"custody:family:{family_id}:{start_date}:{end_date}"
        cached_custody = await redis_service.get(custody_cache_key)
        if cached_custody and len(cached_custody) > 0:
            logger.info(f"Returning cached custody records for {year}/{month} ({len(cached_custody)} records)")
            return cached_custody
        elif cached_custody is not None and len(cached_custody) == 0:
            logger.info(f"Cache returned empty array for {year}/{month}, checking if this is valid...")
            # Empty cache might be valid (no custody records for this month) or invalid (cache corruption)
            # We'll fall through to database query to verify
        
        # Query custody records for the given month and family
        query = custody.select().where(
            (custody.c.family_id == family_id) &
            (custody.c.date.between(start_date, end_date))
        )
        
        db_records = await database.fetch_all(query)
        
        # Get all user data for the family in a single query
        user_query = users.select().where(users.c.family_id == family_id)
        family_users = await database.fetch_all(user_query)
        user_map = {uuid_to_string(user['id']): user['first_name'] for user in family_users}
        
        # Convert records to CustodyResponse format
        custody_responses = [
            CustodyResponse(
                id=record['id'],
                event_date=str(record['date']),
                content=user_map.get(uuid_to_string(record['custodian_id']), "Unknown"),
                custodian_id=uuid_to_string(record['custodian_id']),
                handoff_day=record['handoff_day'],
                handoff_time=record['handoff_time'].strftime('%H:%M') if record['handoff_time'] else None,
                handoff_location=record['handoff_location']
            ) for record in db_records
        ]
        
        # Cache the custody records (convert to dict for JSON serialization)
        custody_responses_dict = [resp.model_dump() for resp in custody_responses]
        await redis_service.set(custody_cache_key, custody_responses_dict, settings.CACHE_TTL_CUSTODY)
        logger.info(f"Cached custody records for {year}/{month} (family {family_id}) - {len(custody_responses)} records")
        
        return custody_responses
    except Exception as e:
        logger.error(f"Error fetching custody records: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/", response_model=CustodyResponse)
async def create_custody(custody_data: CustodyRecord, current_user = Depends(get_current_user)):
    """
    Creates a new custody record for a specific date.
    Returns 409 Conflict if a record already exists for the date.
    """
    logger.info(f"Received custody update request: {custody_data.model_dump_json(indent=2)}")
    
    family_id = current_user['family_id']
    actor_id = current_user['id']
    
    try:
        # Check if a record already exists for this date
        existing_record_query = custody.select().where(
            (custody.c.family_id == family_id) &
            (custody.c.date == custody_data.date)
        )
        existing_record = await database.fetch_one(existing_record_query)
        
        # If handoff_day is not provided, determine it based on default logic
        handoff_day_value = custody_data.handoff_day
        if handoff_day_value is None and custody_data.handoff_time is not None:
            # If handoff time is provided but handoff_day is not, assume it's a handoff day
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
                
                # Set default handoff time and location if not provided
                if not custody_data.handoff_time:
                    weekday = custody_data.date.weekday()  # Monday = 0, Sunday = 6
                    is_weekend = weekday >= 5  # Saturday = 5, Sunday = 6
                    if is_weekend:
                        custody_data.handoff_time = "12:00"  # Noon for weekends
                        if not custody_data.handoff_location:
                            # Get target custodian name for location
                            target_user = await database.fetch_one(users.select().where(users.c.id == custody_data.custodian_id))
                            target_name = target_user['first_name'].lower() if target_user else "unknown"
                            custody_data.handoff_location = f"{target_name}'s home"
                    else:
                        custody_data.handoff_time = "17:00"  # 5pm for weekdays
                        if not custody_data.handoff_location:
                            custody_data.handoff_location = "daycare"
            else:
                handoff_day_value = False

        if existing_record:
            # Return 409 Conflict if record already exists
            raise HTTPException(
                status_code=409, 
                detail=f"Custody record already exists for date {custody_data.date}. Use PUT to update."
            )
        
        # Insert new record only
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
            
        # Send push notification to the other parent
        await send_custody_change_notification(sender_id=actor_id, family_id=family_id, event_date=custody_data.date)
        
        # Invalidate cache for this family since custody affects events display
        await redis_service.clear_family_cache(family_id)
        # Also clear custody-specific cache
        custody_pattern = f"custody:family:{family_id}:*"
        await redis_service.delete_pattern(custody_pattern)
        logger.info(f"Invalidated events and custody cache for family {family_id} after creating custody record")
            
        # Get custodian name for response
        custodian_user = await database.fetch_one(users.select().where(users.c.id == custody_data.custodian_id))
        custodian_name = custodian_user['first_name'] if custodian_user else "Unknown"

        return CustodyResponse(
            id=record_id,
            event_date=str(custody_data.date),
            content=custodian_name,
            custodian_id=str(custody_data.custodian_id),
            handoff_day=handoff_day_value,
            handoff_time=custody_data.handoff_time,
            handoff_location=custody_data.handoff_location
        )
    except Exception as e:
        logger.error(f"Error setting custody: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error while setting custody: {e}")

@router.put("/date/{custody_date}", response_model=CustodyResponse)
async def update_custody_by_date(custody_date: date, custody_data: CustodyRecord, current_user = Depends(get_current_user)):
    """
    Updates an existing custody record for a specific date.
    Returns 404 if no record exists for the date.
    """
    logger.info(f"Received custody UPDATE request for {custody_date}: {custody_data.model_dump_json(indent=2)}")
    
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
            raise HTTPException(status_code=404, detail=f"No custody record found for date {custody_date}")
        
        # Determine handoff_day value
        handoff_day_value = custody_data.handoff_day
        if handoff_day_value is None and custody_data.handoff_time is not None:
            handoff_day_value = True
        elif handoff_day_value is None:
            handoff_day_value = False
        
        # Update the existing record
        update_query = custody.update().where(custody.c.id == existing_record['id']).values(
            custodian_id=custody_data.custodian_id,
            actor_id=actor_id,
            handoff_day=handoff_day_value,
            handoff_time=datetime.strptime(custody_data.handoff_time, '%H:%M').time() if custody_data.handoff_time else None,
            handoff_location=custody_data.handoff_location
        )
        await database.execute(update_query)
        
        # Send push notification to the other parent
        await send_custody_change_notification(sender_id=actor_id, family_id=family_id, event_date=custody_date)
        
        # Invalidate cache for this family since custody affects events display
        await redis_service.clear_family_cache(family_id)
        # Also clear custody-specific cache
        custody_pattern = f"custody:family:{family_id}:*"
        await redis_service.delete_pattern(custody_pattern)
        logger.info(f"Invalidated events and custody cache for family {family_id} after updating custody record")
        
        # Get custodian name for response
        custodian_user = await database.fetch_one(users.select().where(users.c.id == custody_data.custodian_id))
        custodian_name = custodian_user['first_name'] if custodian_user else "Unknown"

        return CustodyResponse(
            id=existing_record['id'],
            event_date=str(custody_date),
            content=custodian_name,
            custodian_id=str(custody_data.custodian_id),
            handoff_day=handoff_day_value,
            handoff_time=custody_data.handoff_time,
            handoff_location=custody_data.handoff_location
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating custody: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error while updating custody: {e}")

@router.put("/{custody_id}", response_model=CustodyResponse)
async def update_custody_by_id(custody_id: int, custody_data: CustodyRecord, current_user = Depends(get_current_user)):
    """
    Updates an existing custody record by ID.
    Returns 404 if record doesn't exist or doesn't belong to user's family.
    """
    logger.info(f"Received custody UPDATE request for ID {custody_id}: {custody_data.model_dump_json(indent=2)}")
    
    family_id = current_user['family_id']
    actor_id = current_user['id']
    
    try:
        # Check if record exists and belongs to family
        existing_record_query = custody.select().where(
            (custody.c.id == custody_id) &
            (custody.c.family_id == family_id)
        )
        existing_record = await database.fetch_one(existing_record_query)
        
        if not existing_record:
            raise HTTPException(status_code=404, detail=f"Custody record {custody_id} not found or access denied")
        
        # Determine handoff_day value
        handoff_day_value = custody_data.handoff_day
        if handoff_day_value is None and custody_data.handoff_time is not None:
            handoff_day_value = True
        elif handoff_day_value is None:
            handoff_day_value = False
        
        # Update the existing record
        update_query = custody.update().where(custody.c.id == custody_id).values(
            custodian_id=custody_data.custodian_id,
            actor_id=actor_id,
            handoff_day=handoff_day_value,
            handoff_time=datetime.strptime(custody_data.handoff_time, '%H:%M').time() if custody_data.handoff_time else None,
            handoff_location=custody_data.handoff_location
        )
        await database.execute(update_query)
        
        # Send push notification to the other parent
        await send_custody_change_notification(sender_id=actor_id, family_id=family_id, event_date=custody_data.date)
        
        # Invalidate cache for this family since custody affects events display
        await redis_service.clear_family_cache(family_id)
        # Also clear custody-specific cache
        custody_pattern = f"custody:family:{family_id}:*"
        await redis_service.delete_pattern(custody_pattern)
        logger.info(f"Invalidated events and custody cache for family {family_id} after updating custody record by ID")
        
        # Get custodian name for response
        custodian_user = await database.fetch_one(users.select().where(users.c.id == custody_data.custodian_id))
        custodian_name = custodian_user['first_name'] if custodian_user else "Unknown"

        return CustodyResponse(
            id=custody_id,
            event_date=str(custody_data.date),
            content=custodian_name,
            custodian_id=str(custody_data.custodian_id),
            handoff_day=handoff_day_value,
            handoff_time=custody_data.handoff_time,
            handoff_location=custody_data.handoff_location
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating custody: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error while updating custody: {e}")

@router.post("/bulk", response_model=dict)
async def bulk_create_custody(custody_records: List[CustodyRecord], current_user = Depends(get_current_user)):
    """
    Creates multiple custody records in a single transaction for improved performance.
    Useful for onboarding or schedule template applications.
    """
    logger.info(f"Received bulk custody creation request for {len(custody_records)} records")
    
    family_id = current_user['family_id']
    actor_id = current_user['id']
    
    try:
        # Sort records by date to properly detect handoffs
        sorted_records = sorted(custody_records, key=lambda x: x.date)
        
        # Prepare bulk insert data
        insert_values = []
        previous_custodian_id = None
        
        for custody_data in sorted_records:
            # Determine handoff_day value
            handoff_day_value = custody_data.handoff_day
            handoff_time_value = custody_data.handoff_time
            handoff_location_value = custody_data.handoff_location
            
            # Auto-detect handoff if not explicitly set
            if handoff_day_value is None:
                is_handoff_day = (previous_custodian_id is not None and 
                                previous_custodian_id != custody_data.custodian_id)
                handoff_day_value = is_handoff_day
                
                # Set default handoff time and location for detected handoffs
                if is_handoff_day and not handoff_time_value:
                    weekday = custody_data.date.weekday()  # Monday = 0, Sunday = 6
                    is_weekend = weekday >= 5  # Saturday = 5, Sunday = 6
                    
                    if is_weekend:
                        handoff_time_value = "12:00"  # Noon for weekends
                        if not handoff_location_value:
                            handoff_location_value = "other"
                    else:
                        handoff_time_value = "17:00"  # 5pm for weekdays
                        if not handoff_location_value:
                            handoff_location_value = "daycare"
            
            insert_values.append({
                'family_id': family_id,
                'date': custody_data.date,
                'custodian_id': custody_data.custodian_id,
                'actor_id': actor_id,
                'handoff_day': handoff_day_value,
                'handoff_time': datetime.strptime(handoff_time_value, '%H:%M').time() if handoff_time_value else None,
                'handoff_location': handoff_location_value,
                'created_at': datetime.now()
            })
            
            previous_custodian_id = custody_data.custodian_id
        
        # Perform bulk insert
        if insert_values:
            # Use PostgreSQL's bulk insert for efficiency
            insert_query = custody.insert()
            await database.execute_many(insert_query, insert_values)
            
            logger.info(f"Successfully created {len(insert_values)} custody records via bulk insert")
            
            # Invalidate cache for this family since custody affects events display
            await redis_service.clear_family_cache(family_id)
            # Also clear custody-specific cache
            custody_pattern = f"custody:family:{family_id}:*"
            await redis_service.delete_pattern(custody_pattern)
            logger.info(f"Invalidated events and custody cache for family {family_id} after bulk creating custody records")
            
            return {
                "status": "success",
                "records_created": len(insert_values),
                "message": f"Successfully created {len(insert_values)} custody records"
            }
        else:
            return {
                "status": "success", 
                "records_created": 0,
                "message": "No records to create"
            }
            
    except Exception as e:
        logger.error(f"Error in bulk custody creation: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error during bulk custody creation: {e}")
