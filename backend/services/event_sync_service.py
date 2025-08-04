import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from core.database import database
from core.logging import logger
from db.models import school_calendar_syncs, daycare_calendar_syncs, school_providers, daycare_providers
from services.school_events_service import parse_events_from_url, store_school_events
from services.daycare_events_service import parse_events_from_url as parse_daycare_events, store_daycare_events

async def sync_school_events(school_provider_id: int, calendar_url: str) -> Dict[str, Any]:
    """
    Sync events for a specific school provider.
    Returns sync status including success, event count, and any errors.
    """
    try:
        logger.info(f"Starting sync for school provider {school_provider_id}")
        
        # Get school provider details
        provider_query = school_providers.select().where(school_providers.c.id == school_provider_id)
        provider = await database.fetch_one(provider_query)
        
        if not provider:
            raise ValueError(f"School provider {school_provider_id} not found")
        
        # Parse events from the calendar URL
        events = await parse_events_from_url(calendar_url)
        
        # Store events
        if events:
            await store_school_events(school_provider_id, events, provider['name'])
        
        # Update sync record
        sync_data = {
            "last_sync_at": datetime.now(timezone.utc),
            "last_sync_success": True,
            "last_sync_error": None,
            "events_count": len(events) if events else 0
        }
        
        await database.execute(
            school_calendar_syncs.update()
            .where(
                (school_calendar_syncs.c.school_provider_id == school_provider_id) &
                (school_calendar_syncs.c.calendar_url == calendar_url)
            )
            .values(**sync_data)
        )
        
        return {
            "success": True,
            "events_count": len(events) if events else 0,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Error syncing school events for provider {school_provider_id}: {e}")
        
        # Update sync record with error
        sync_data = {
            "last_sync_at": datetime.now(timezone.utc),
            "last_sync_success": False,
            "last_sync_error": str(e)
        }
        
        await database.execute(
            school_calendar_syncs.update()
            .where(
                (school_calendar_syncs.c.school_provider_id == school_provider_id) &
                (school_calendar_syncs.c.calendar_url == calendar_url)
            )
            .values(**sync_data)
        )
        
        return {
            "success": False,
            "events_count": 0,
            "error": str(e)
        }

async def sync_daycare_events(daycare_provider_id: int, calendar_url: str) -> Dict[str, Any]:
    """
    Sync events for a specific daycare provider.
    Returns sync status including success, event count, and any errors.
    """
    try:
        logger.info(f"Starting sync for daycare provider {daycare_provider_id}")
        
        # Get daycare provider details
        provider_query = daycare_providers.select().where(daycare_providers.c.id == daycare_provider_id)
        provider = await database.fetch_one(provider_query)
        
        if not provider:
            raise ValueError(f"Daycare provider {daycare_provider_id} not found")
        
        # Parse events from the calendar URL
        events = await parse_daycare_events(calendar_url)
        
        # Store events
        if events:
            await store_daycare_events(daycare_provider_id, events, provider['name'])
        
        # Update sync record
        sync_data = {
            "last_sync_at": datetime.now(timezone.utc),
            "last_sync_success": True,
            "last_sync_error": None,
            "events_count": len(events) if events else 0
        }
        
        await database.execute(
            daycare_calendar_syncs.update()
            .where(
                (daycare_calendar_syncs.c.daycare_provider_id == daycare_provider_id) &
                (daycare_calendar_syncs.c.calendar_url == calendar_url)
            )
            .values(**sync_data)
        )
        
        return {
            "success": True,
            "events_count": len(events) if events else 0,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Error syncing daycare events for provider {daycare_provider_id}: {e}")
        
        # Update sync record with error
        sync_data = {
            "last_sync_at": datetime.now(timezone.utc),
            "last_sync_success": False,
            "last_sync_error": str(e)
        }
        
        await database.execute(
            daycare_calendar_syncs.update()
            .where(
                (daycare_calendar_syncs.c.daycare_provider_id == daycare_provider_id) &
                (daycare_calendar_syncs.c.calendar_url == calendar_url)
            )
            .values(**sync_data)
        )
        
        return {
            "success": False,
            "events_count": 0,
            "error": str(e)
        }

async def sync_all_enabled_calendars():
    """
    Sync all enabled school and daycare calendars.
    This should be called periodically (e.g., daily) by a cron job or scheduler.
    """
    logger.info("Starting sync for all enabled calendars")
    
    results = {
        "schools": {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "events_synced": 0
        },
        "daycares": {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "events_synced": 0
        }
    }
    
    # Sync school calendars
    school_syncs_query = school_calendar_syncs.select().where(
        school_calendar_syncs.c.sync_enabled == True
    )
    school_syncs = await database.fetch_all(school_syncs_query)
    
    for sync in school_syncs:
        results["schools"]["total"] += 1
        sync_result = await sync_school_events(
            sync['school_provider_id'], 
            sync['calendar_url']
        )
        
        if sync_result["success"]:
            results["schools"]["successful"] += 1
            results["schools"]["events_synced"] += sync_result["events_count"]
        else:
            results["schools"]["failed"] += 1
    
    # Sync daycare calendars
    daycare_syncs_query = daycare_calendar_syncs.select().where(
        daycare_calendar_syncs.c.sync_enabled == True
    )
    daycare_syncs = await database.fetch_all(daycare_syncs_query)
    
    for sync in daycare_syncs:
        results["daycares"]["total"] += 1
        sync_result = await sync_daycare_events(
            sync['daycare_provider_id'], 
            sync['calendar_url']
        )
        
        if sync_result["success"]:
            results["daycares"]["successful"] += 1
            results["daycares"]["events_synced"] += sync_result["events_count"]
        else:
            results["daycares"]["failed"] += 1
    
    logger.info(f"Sync completed. Results: {results}")
    return results

async def disable_failing_syncs(failure_threshold: int = 5):
    """
    Disable calendar syncs that have failed multiple times in a row.
    This prevents continuous retries of broken calendars.
    """
    # This could be enhanced to track consecutive failures
    # For now, it's a placeholder for future implementation
    pass