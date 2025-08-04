from typing import Optional
from core.database import database
from core.logging import logger
from db.models import families, daycare_calendar_syncs, school_calendar_syncs, daycare_providers, school_providers

async def assign_daycare_sync_to_family(daycare_provider_id: int, calendar_sync_id: int) -> bool:
    """
    Assign a daycare calendar sync to the family that owns the daycare provider.
    
    Args:
        daycare_provider_id: The daycare provider ID
        calendar_sync_id: The daycare calendar sync ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get the family_id from the daycare provider
        provider_query = daycare_providers.select().where(daycare_providers.c.id == daycare_provider_id)
        provider = await database.fetch_one(provider_query)
        
        if not provider:
            logger.error(f"Daycare provider {daycare_provider_id} not found")
            return False
        
        family_id = provider['family_id']
        
        # Update the family with the daycare sync
        update_query = families.update().where(families.c.id == family_id).values(
            daycare_sync_id=calendar_sync_id
        )
        await database.execute(update_query)
        
        logger.info(f"Assigned daycare sync {calendar_sync_id} to family {family_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error assigning daycare sync to family: {e}")
        return False

async def assign_school_sync_to_family(school_provider_id: int, calendar_sync_id: int) -> bool:
    """
    Assign a school calendar sync to the family that owns the school provider.
    
    Args:
        school_provider_id: The school provider ID
        calendar_sync_id: The school calendar sync ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get the family_id from the school provider
        provider_query = school_providers.select().where(school_providers.c.id == school_provider_id)
        provider = await database.fetch_one(provider_query)
        
        if not provider:
            logger.error(f"School provider {school_provider_id} not found")
            return False
        
        family_id = provider['family_id']
        
        # Update the family with the school sync
        update_query = families.update().where(families.c.id == family_id).values(
            school_sync_id=calendar_sync_id
        )
        await database.execute(update_query)
        
        logger.info(f"Assigned school sync {calendar_sync_id} to family {family_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error assigning school sync to family: {e}")
        return False

async def remove_daycare_sync_from_family(family_id: str) -> bool:
    """
    Remove daycare sync assignment from a family.
    
    Args:
        family_id: The family ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        update_query = families.update().where(families.c.id == family_id).values(
            daycare_sync_id=None
        )
        await database.execute(update_query)
        
        logger.info(f"Removed daycare sync from family {family_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error removing daycare sync from family: {e}")
        return False

async def remove_school_sync_from_family(family_id: str) -> bool:
    """
    Remove school sync assignment from a family.
    
    Args:
        family_id: The family ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        update_query = families.update().where(families.c.id == family_id).values(
            school_sync_id=None
        )
        await database.execute(update_query)
        
        logger.info(f"Removed school sync from family {family_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error removing school sync from family: {e}")
        return False

async def get_family_daycare_events(family_id: str) -> list:
    """
    Get all daycare events for a family based on their sync agreement.
    
    Args:
        family_id: The family ID
        
    Returns:
        list: List of daycare events
    """
    try:
        query = """
        SELECT de.*, dp.name as daycare_name
        FROM daycare_events de
        JOIN daycare_calendar_syncs dcs ON de.daycare_provider_id = dcs.daycare_provider_id
        JOIN families f ON f.daycare_sync_id = dcs.id
        JOIN daycare_providers dp ON de.daycare_provider_id = dp.id
        WHERE f.id = :family_id AND dcs.sync_enabled = TRUE
        ORDER BY de.event_date
        """
        
        events = await database.fetch_all(query, {'family_id': family_id})
        return [dict(event) for event in events]
        
    except Exception as e:
        logger.error(f"Error getting family daycare events: {e}")
        return []

async def get_family_school_events(family_id: str) -> list:
    """
    Get all school events for a family based on their sync agreement.
    
    Args:
        family_id: The family ID
        
    Returns:
        list: List of school events
    """
    try:
        query = """
        SELECT se.*, sp.name as school_name
        FROM school_events se
        JOIN school_calendar_syncs scs ON se.school_provider_id = scs.school_provider_id
        JOIN families f ON f.school_sync_id = scs.id
        JOIN school_providers sp ON se.school_provider_id = sp.id
        WHERE f.id = :family_id AND scs.sync_enabled = TRUE
        ORDER BY se.event_date
        """
        
        events = await database.fetch_all(query, {'family_id': family_id})
        return [dict(event) for event in events]
        
    except Exception as e:
        logger.error(f"Error getting family school events: {e}")
        return [] 