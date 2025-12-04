"""
Custody Generator Service
Handles automatic generation of custody records from schedule templates.
"""

import json
import logging
from datetime import date, datetime, timedelta, time
from typing import List, Dict, Optional, Any
from db.models import custody, schedule_templates, users
from core.database import database
from services.redis_service import redis_service

logger = logging.getLogger(__name__)

class CustodyGenerator:
    """Service for generating custody records from schedule templates."""
    
    @staticmethod
    async def get_active_template(family_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the active schedule template for a family.
        
        Args:
            family_id: The family ID to get the template for
            
        Returns:
            The active template record or None if no active template exists
        """
        try:
            template_query = schedule_templates.select().where(
                (schedule_templates.c.family_id == family_id) &
                (schedule_templates.c.is_active == True)
            )
            template_record = await database.fetch_one(template_query)
            return dict(template_record) if template_record else None
        except Exception as e:
            logger.error(f"Error fetching active template for family {family_id}: {e}")
            return None
    
    @staticmethod
    async def get_family_custodians(family_id: str) -> tuple[Optional[str], Optional[str]]:
        """
        Get the two primary custodians for a family.
        
        Args:
            family_id: The family ID
            
        Returns:
            Tuple of (parent1_id, parent2_id) or (None, None) if not enough members
        """
        try:
            custodians_query = users.select().where(
                users.c.family_id == family_id
            ).order_by(users.c.created_at.asc().nulls_last())
            
            family_members = await database.fetch_all(custodians_query)
            
            if len(family_members) >= 2:
                return str(family_members[0]['id']), str(family_members[1]['id'])
            
            logger.warning(f"Family {family_id} has less than 2 members")
            return None, None
        except Exception as e:
            logger.error(f"Error fetching custodians for family {family_id}: {e}")
            return None, None
    
    @staticmethod
    async def generate_custody_from_template(
        template: Dict[str, Any],
        start_date: date,
        end_date: date,
        family_id: str,
        actor_id: str,
        respect_existing: bool = True
    ) -> int:
        """
        Generate custody records from a schedule template for a date range.
        
        Args:
            template: The schedule template record
            start_date: Start date for generation
            end_date: End date for generation
            family_id: The family ID
            actor_id: The user ID performing the action
            respect_existing: If True, won't overwrite existing records
            
        Returns:
            Number of custody records created
        """
        try:
            # Ensure we never modify past dates
            today = date.today()
            if start_date <= today:
                start_date = today + timedelta(days=1)
            
            if end_date <= start_date:
                logger.warning(f"End date {end_date} is not after start date {start_date}")
                return 0
            
            # Get custodian IDs
            parent1_id, parent2_id = await CustodyGenerator.get_family_custodians(family_id)
            if not parent1_id or not parent2_id:
                logger.error(f"Cannot generate custody: family {family_id} needs 2 members")
                return 0
            
            # Parse the pattern
            if template['pattern_type'] != 'weekly':
                logger.error(f"Unsupported pattern type: {template['pattern_type']}")
                return 0
            
            pattern_data = template['weekly_pattern']
            if isinstance(pattern_data, str):
                try:
                    pattern_data = json.loads(pattern_data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in weekly_pattern for template {template['id']}")
                    return 0
            
            if not pattern_data:
                logger.error(f"No weekly pattern found in template {template['id']}")
                return 0
            
            # Get existing records if we need to respect them
            existing_by_date = {}
            if respect_existing:
                existing_query = custody.select().where(
                    (custody.c.family_id == family_id) &
                    (custody.c.date.between(start_date, end_date))
                )
                existing_records = await database.fetch_all(existing_query)
                existing_by_date = {record['date']: record for record in existing_records}
            
            # Get the last custody record before start_date to determine previous custodian
            previous_custodian_id = await CustodyGenerator._get_previous_custodian(
                family_id, start_date
            )
            
            # Generate records
            records_to_create = []
            current_date = start_date
            
            while current_date <= end_date:
                # Skip if record exists and we're respecting existing
                if respect_existing and current_date in existing_by_date:
                    # Still update previous custodian for handoff calculation
                    previous_custodian_id = str(existing_by_date[current_date]['custodian_id'])
                    current_date += timedelta(days=1)
                    continue
                
                day_of_week = current_date.strftime('%A').lower()
                
                if day_of_week in pattern_data and pattern_data[day_of_week]:
                    custodian_assignment = pattern_data[day_of_week]
                    
                    # Map logical assignment to actual custodian ID
                    actual_custodian_id = None
                    if custodian_assignment == 'parent1':
                        actual_custodian_id = parent1_id
                    elif custodian_assignment == 'parent2':
                        actual_custodian_id = parent2_id
                    
                    if actual_custodian_id:
                        # Determine if this is a handoff day
                        is_handoff_day = (
                            previous_custodian_id is not None and 
                            previous_custodian_id != actual_custodian_id
                        )
                        
                        # Set handoff time and location for handoff days
                        handoff_time = None
                        handoff_location = None
                        
                        if is_handoff_day:
                            weekday = current_date.weekday()
                            is_weekend = weekday >= 5
                            
                            if is_weekend:
                                handoff_time = time(12, 0)  # Noon for weekends
                                handoff_location = "other"
                            else:
                                handoff_time = time(17, 0)  # 5pm for weekdays
                                handoff_location = "daycare"
                        
                        records_to_create.append({
                            'family_id': family_id,
                            'date': current_date,
                            'custodian_id': actual_custodian_id,
                            'actor_id': actor_id,
                            'handoff_day': is_handoff_day,
                            'handoff_time': handoff_time,
                            'handoff_location': handoff_location,
                            'created_at': datetime.now(),
                            'updated_at': datetime.now()
                        })
                        
                        # Update previous custodian for next iteration
                        previous_custodian_id = actual_custodian_id
                
                current_date += timedelta(days=1)
            
            # Bulk insert records if any were generated
            if records_to_create:
                insert_query = custody.insert()
                await database.execute_many(insert_query, records_to_create)
                
                # Invalidate cache for affected months
                affected_months = set(
                    (record['date'].year, record['date'].month) 
                    for record in records_to_create
                )
                for year, month in affected_months:
                    cache_key = f"custody_opt:family:{family_id}:{year}:{month:02d}"
                    await redis_service.delete(cache_key)
                    handoff_key = f"handoff_only:family:{family_id}:{year}:{month:02d}"
                    await redis_service.delete(handoff_key)
                
                logger.info(f"Generated {len(records_to_create)} custody records for family {family_id}")
                return len(records_to_create)
            
            return 0
            
        except Exception as e:
            logger.error(f"Error generating custody from template: {e}", exc_info=True)
            return 0
    
    @staticmethod
    async def _get_previous_custodian(family_id: str, before_date: date) -> Optional[str]:
        """
        Get the custodian ID from the last custody record before a given date.
        
        Args:
            family_id: The family ID
            before_date: Get the record before this date
            
        Returns:
            The custodian ID or None if no previous record exists
        """
        try:
            # Get the most recent custody record before the start date
            query = custody.select().where(
                (custody.c.family_id == family_id) &
                (custody.c.date < before_date)
            ).order_by(custody.c.date.desc()).limit(1)
            
            record = await database.fetch_one(query)
            return str(record['custodian_id']) if record else None
        except Exception as e:
            logger.error(f"Error fetching previous custodian: {e}")
            return None
    
    @staticmethod
    async def auto_generate_for_month(
        family_id: str,
        year: int,
        month: int,
        actor_id: str
    ) -> int:
        """
        Auto-generate custody records for a specific month if an active template exists.
        Only generates for future dates.
        
        Args:
            family_id: The family ID
            year: Year to generate for
            month: Month to generate for
            actor_id: The user ID performing the action
            
        Returns:
            Number of records generated
        """
        try:
            from calendar import monthrange
            
            # Get the active template
            template = await CustodyGenerator.get_active_template(family_id)
            if not template:
                logger.info(f"No active template for family {family_id}, skipping auto-generation")
                return 0
            
            # Calculate date range for the month
            start_date = date(year, month, 1)
            _, last_day = monthrange(year, month)
            end_date = date(year, month, last_day)
            
            # Only generate for future dates
            today = date.today()
            if end_date <= today:
                logger.info(f"Month {year}/{month} is in the past, skipping auto-generation")
                return 0
            
            # Adjust start date if it's in the past
            if start_date <= today:
                start_date = today + timedelta(days=1)
            
            logger.info(f"Auto-generating custody for family {family_id} for {year}/{month}")
            
            # Generate custody records
            return await CustodyGenerator.generate_custody_from_template(
                template=template,
                start_date=start_date,
                end_date=end_date,
                family_id=family_id,
                actor_id=actor_id,
                respect_existing=True
            )
            
        except Exception as e:
            logger.error(f"Error in auto-generation for month: {e}", exc_info=True)
            return 0
