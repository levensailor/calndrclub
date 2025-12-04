from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime, date, timedelta
import json

from core.database import database
from core.security import get_current_user, uuid_to_string
from core.logging import logger
from db.models import schedule_templates, custody
from services.redis_service import redis_service
from services.custody_generator import CustodyGenerator
from schemas.schedule import (
    ScheduleTemplate, ScheduleTemplateCreate, ScheduleApplication, 
    ScheduleApplicationResponse, SchedulePatternType, WeeklySchedulePattern,
    AlternatingWeeksPattern
)

router = APIRouter()

@router.get("/", response_model=List[ScheduleTemplate])
async def get_schedule_templates(current_user = Depends(get_current_user)):
    """
    Get all schedule templates for the current user's family.
    """
    try:
        query = schedule_templates.select().where(
            schedule_templates.c.family_id == current_user['family_id']
        ).order_by(schedule_templates.c.created_at.desc())
        
        template_records = await database.fetch_all(query)
        
        templates = []
        for record in template_records:
            weekly_pattern = None
            if 'weekly_pattern' in record and record['weekly_pattern']:
                try:
                    pattern_data = record['weekly_pattern']
                    if isinstance(pattern_data, str):
                        pattern_data = json.loads(pattern_data)
                    weekly_pattern = WeeklySchedulePattern(**pattern_data)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.error(f"Error deserializing weekly pattern for template {record['id']}: {e}")

            alternating_weeks_pattern = None
            if 'alternating_weeks_pattern' in record and record['alternating_weeks_pattern']:
                try:
                    pattern_data = record['alternating_weeks_pattern']
                    if isinstance(pattern_data, str):
                        pattern_data = json.loads(pattern_data)
                    alternating_weeks_pattern = AlternatingWeeksPattern(**pattern_data)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.error(f"Error deserializing alternating weeks pattern for template {record['id']}: {e}")

            templates.append(ScheduleTemplate(
                id=record['id'],
                name=record['name'],
                description=record['description'],
                pattern_type=record['pattern_type'],
                weekly_pattern=weekly_pattern,
                alternating_weeks_pattern=alternating_weeks_pattern,
                is_active=record['is_active'],
                family_id=uuid_to_string(record['family_id']),
                created_at=str(record['created_at']),
                updated_at=str(record['updated_at'])
            ))
        
        return templates
    except Exception as e:
        logger.error(f"Error fetching schedule templates: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch schedule templates: {str(e)}"
        )

@router.get("/{template_id}", response_model=ScheduleTemplate)
async def get_schedule_template(template_id: int, current_user = Depends(get_current_user)):
    """
    Get a specific schedule template by ID for the current user's family.
    """
    try:
        query = schedule_templates.select().where(
            (schedule_templates.c.id == template_id) &
            (schedule_templates.c.family_id == current_user['family_id'])
        )
        
        template_record = await database.fetch_one(query)
        
        if not template_record:
            raise HTTPException(status_code=404, detail="Schedule template not found")
        
        # Deserialize pattern data from JSON
        weekly_pattern = None
        if 'weekly_pattern' in template_record and template_record['weekly_pattern']:
            try:
                pattern_data = template_record['weekly_pattern']
                if isinstance(pattern_data, str):
                    pattern_data = json.loads(pattern_data)
                weekly_pattern = WeeklySchedulePattern(**pattern_data)
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Error deserializing weekly pattern for template {template_id}: {e}")

        alternating_weeks_pattern = None
        if 'alternating_weeks_pattern' in template_record and template_record['alternating_weeks_pattern']:
            try:
                pattern_data = template_record['alternating_weeks_pattern']
                if isinstance(pattern_data, str):
                    pattern_data = json.loads(pattern_data)
                alternating_weeks_pattern = AlternatingWeeksPattern(**pattern_data)
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Error deserializing alternating weeks pattern for template {template_id}: {e}")
        
        return ScheduleTemplate(
            id=template_record['id'],
            name=template_record['name'],
            description=template_record['description'],
            pattern_type=template_record['pattern_type'],
            weekly_pattern=weekly_pattern,
            alternating_weeks_pattern=alternating_weeks_pattern,
            is_active=template_record['is_active'],
            family_id=uuid_to_string(template_record['family_id']),
            created_at=str(template_record['created_at']),
            updated_at=str(template_record['updated_at'])
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching schedule template {template_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch schedule template {template_id}: {str(e)}"
        )

@router.post("/", response_model=ScheduleTemplate)
async def create_schedule_template(template_data: ScheduleTemplateCreate, current_user = Depends(get_current_user)):
    """
    Create a new schedule template for the current user's family.
    If this template is marked as active, all other templates will be marked as inactive.
    """
    try:
        logger.info(f"Creating schedule template: {template_data.name}")
        logger.info(f"Pattern type: {template_data.pattern_type}")
        
        # If this template is being set as active, deactivate all other templates for this family
        if template_data.is_active:
            deactivate_query = schedule_templates.update().where(
                schedule_templates.c.family_id == current_user['family_id']
            ).values(is_active=False, updated_at=datetime.now())
            await database.execute(deactivate_query)
            logger.info(f"Deactivated all existing schedule templates for family {current_user['family_id']}")
        
        # Convert pattern data to JSON
        weekly_pattern_json = template_data.weekly_pattern.dict() if template_data.weekly_pattern else None
        alternating_pattern_json = template_data.alternating_weeks_pattern.dict() if template_data.alternating_weeks_pattern else None
        
        # Log the weekly pattern to debug parent assignments
        if weekly_pattern_json:
            logger.info(f"Weekly pattern received from iOS:")
            for day, assignment in weekly_pattern_json.items():
                logger.info(f"  {day}: {assignment}")
        
        insert_query = schedule_templates.insert().values(
            family_id=current_user['family_id'],
            name=template_data.name,
            description=template_data.description,
            pattern_type=template_data.pattern_type,
            weekly_pattern=weekly_pattern_json,
            alternating_weeks_pattern=alternating_pattern_json,
            is_active=template_data.is_active,
            created_by_user_id=current_user['id'],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        template_id = await database.execute(insert_query)
        
        # Fetch the created template
        template_record = await database.fetch_one(
            schedule_templates.select().where(schedule_templates.c.id == template_id)
        )
        
        logger.info(f"Raw template record from database: {dict(template_record)}")
        
        # Deserialize pattern data from JSON for the response
        weekly_pattern = None
        if 'weekly_pattern' in template_record and template_record['weekly_pattern']:
            try:
                pattern_data = template_record['weekly_pattern']
                if isinstance(pattern_data, str):
                    pattern_data = json.loads(pattern_data)
                weekly_pattern = WeeklySchedulePattern(**pattern_data)
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Error deserializing created weekly pattern for template {template_id}: {e}")
        
        alternating_weeks_pattern = None
        if 'alternating_weeks_pattern' in template_record and template_record['alternating_weeks_pattern']:
            try:
                pattern_data = template_record['alternating_weeks_pattern']
                if isinstance(pattern_data, str):
                    pattern_data = json.loads(pattern_data)
                alternating_weeks_pattern = AlternatingWeeksPattern(**pattern_data)
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Error deserializing created alternating weeks pattern for template {template_id}: {e}")
        
        response = ScheduleTemplate(
            id=template_record['id'],
            name=template_record['name'],
            description=template_record['description'],
            pattern_type=template_record['pattern_type'],
            weekly_pattern=weekly_pattern,
            alternating_weeks_pattern=alternating_weeks_pattern,
            is_active=template_record['is_active'],
            family_id=uuid_to_string(template_record['family_id']),
            created_at=str(template_record['created_at']),
            updated_at=str(template_record['updated_at'])
        )
        
        logger.info(f"Pydantic response object: {response.model_dump()}")
        logger.info(f"JSON response: {response.model_dump_json()}")
        
        return response
    except Exception as e:
        logger.error(f"Error creating schedule template: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create schedule template: {str(e)}"
        )

@router.put("/{template_id}", response_model=ScheduleTemplate)
async def update_schedule_template(template_id: int, template_data: ScheduleTemplateCreate, current_user = Depends(get_current_user)):
    """
    Update a schedule template that belongs to the current user's family.
    If this template is being set as active, all other templates will be marked as inactive.
    """
    try:
        # Check if template exists and belongs to user's family
        check_query = schedule_templates.select().where(
            (schedule_templates.c.id == template_id) &
            (schedule_templates.c.family_id == current_user['family_id'])
        )
        existing = await database.fetch_one(check_query)
        
        if not existing:
            raise HTTPException(status_code=404, detail="Schedule template not found")
        
        # If this template is being set as active, deactivate all other templates for this family
        if template_data.is_active:
            deactivate_query = schedule_templates.update().where(
                (schedule_templates.c.family_id == current_user['family_id']) &
                (schedule_templates.c.id != template_id)
            ).values(is_active=False, updated_at=datetime.now())
            await database.execute(deactivate_query)
            logger.info(f"Deactivated other schedule templates for family {current_user['family_id']} when setting template {template_id} as active")
        
        # Convert pattern data to JSON
        weekly_pattern_json = template_data.weekly_pattern.dict() if template_data.weekly_pattern else None
        alternating_pattern_json = template_data.alternating_weeks_pattern.dict() if template_data.alternating_weeks_pattern else None
        
        # Update the template
        update_query = schedule_templates.update().where(schedule_templates.c.id == template_id).values(
            name=template_data.name,
            description=template_data.description,
            pattern_type=template_data.pattern_type,
            weekly_pattern=weekly_pattern_json,
            alternating_weeks_pattern=alternating_pattern_json,
            is_active=template_data.is_active,
            updated_at=datetime.now()
        )
        await database.execute(update_query)
        
        # Fetch the updated template
        template_record = await database.fetch_one(
            schedule_templates.select().where(schedule_templates.c.id == template_id)
        )
        
        # Deserialize pattern data from JSON
        weekly_pattern = None
        if 'weekly_pattern' in template_record and template_record['weekly_pattern']:
            try:
                pattern_data = template_record['weekly_pattern']
                if isinstance(pattern_data, str):
                    pattern_data = json.loads(pattern_data)
                weekly_pattern = WeeklySchedulePattern(**pattern_data)
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Error deserializing updated weekly pattern for template {template_id}: {e}")

        alternating_weeks_pattern = None
        if 'alternating_weeks_pattern' in template_record and template_record['alternating_weeks_pattern']:
            try:
                pattern_data = template_record['alternating_weeks_pattern']
                if isinstance(pattern_data, str):
                    pattern_data = json.loads(pattern_data)
                alternating_weeks_pattern = AlternatingWeeksPattern(**pattern_data)
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Error deserializing updated alternating weeks pattern for template {template_id}: {e}")

        return ScheduleTemplate(
            id=template_record['id'],
            name=template_record['name'],
            description=template_record['description'],
            pattern_type=template_record['pattern_type'],
            weekly_pattern=weekly_pattern,
            alternating_weeks_pattern=alternating_weeks_pattern,
            is_active=template_record['is_active'],
            family_id=uuid_to_string(template_record['family_id']),
            created_at=str(template_record['created_at']),
            updated_at=str(template_record['updated_at'])
        )
    except Exception as e:
        logger.error(f"Error updating schedule template: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update schedule template: {str(e)}"
        )

@router.delete("/{template_id}")
async def delete_schedule_template(template_id: int, current_user = Depends(get_current_user)):
    """
    Delete a schedule template that belongs to the current user's family.
    """
    try:
        # Check if template exists and belongs to user's family
        check_query = schedule_templates.select().where(
            (schedule_templates.c.id == template_id) &
            (schedule_templates.c.family_id == current_user['family_id'])
        )
        existing = await database.fetch_one(check_query)
        
        if not existing:
            raise HTTPException(status_code=404, detail="Schedule template not found")
        
        # Delete the template
        delete_query = schedule_templates.delete().where(schedule_templates.c.id == template_id)
        await database.execute(delete_query)
        
        return {"status": "success", "message": "Schedule template deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting schedule template: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete schedule template: {str(e)}"
        )

@router.post("/apply", response_model=ScheduleApplicationResponse)
async def apply_schedule_template(application: ScheduleApplication, current_user = Depends(get_current_user)):
    """
    Apply a schedule template to future dates, creating custody records.
    The applied template will be marked as the current active template.
    Always starts from tomorrow and generates 90 days of records.
    Past custody events are never modified.
    """
    try:
        # Get the template
        template_query = schedule_templates.select().where(
            (schedule_templates.c.id == application.template_id) &
            (schedule_templates.c.family_id == current_user['family_id'])
        )
        template_record = await database.fetch_one(template_query)
        
        if not template_record:
            raise HTTPException(status_code=404, detail="Schedule template not found")
        
        # Mark this template as active and deactivate all others
        deactivate_query = schedule_templates.update().where(
            (schedule_templates.c.family_id == current_user['family_id']) &
            (schedule_templates.c.id != application.template_id)
        ).values(is_active=False, updated_at=datetime.now())
        await database.execute(deactivate_query)
        
        activate_query = schedule_templates.update().where(
            schedule_templates.c.id == application.template_id
        ).values(is_active=True, updated_at=datetime.now())
        await database.execute(activate_query)
        
        logger.info(f"Set template {application.template_id} as active when applying schedule")
        
        # Always start from tomorrow, never modify past or today's custody
        tomorrow = (datetime.now().date() + timedelta(days=1))
        
        # If application specified dates, use them but ensure they're in the future
        if application.start_date and application.end_date:
            requested_start = datetime.fromisoformat(application.start_date.replace('Z', '+00:00')).date()
            requested_end = datetime.fromisoformat(application.end_date.replace('Z', '+00:00')).date()
            # Use the later of tomorrow or requested start
            start_date = max(tomorrow, requested_start)
            # Use requested end if it's in the future, otherwise 90 days from start
            if requested_end > start_date:
                end_date = requested_end
            else:
                end_date = start_date + timedelta(days=90)
        else:
            # Default: tomorrow + 90 days
            start_date = tomorrow
            end_date = tomorrow + timedelta(days=90)
        
        logger.info(f"Applying template from {start_date} to {end_date}")
        
        family_id = current_user['family_id']
        
        # Use the custody generator service to apply the template
        days_applied = await CustodyGenerator.generate_custody_from_template(
            template=dict(template_record),
            start_date=start_date,
            end_date=end_date,
            family_id=family_id,
            actor_id=current_user['id'],
            respect_existing=not application.overwrite_existing  # Invert the flag
        )
        
        # Count any conflicts that were overwritten (if overwrite was enabled)
        conflicts_overwritten = 0
        if application.overwrite_existing:
            # Query to count how many existing future records were in the range
            from db.models import custody
            existing_query = custody.select().where(
                (custody.c.family_id == family_id) &
                (custody.c.date.between(start_date, end_date)) &
                (custody.c.date > datetime.now().date())
            )
            existing_records = await database.fetch_all(existing_query)
            conflicts_overwritten = len(existing_records)
        
        # Invalidate cache for this family since we created/updated custody records
        await redis_service.clear_family_cache(family_id)
        logger.info(f"Invalidated events cache for family {family_id} after applying schedule template")
        
        return ScheduleApplicationResponse(
            success=True,
            message=f"Applied schedule template '{template_record['name']}' to {days_applied} days",
            days_applied=days_applied,
            conflicts_overwritten=conflicts_overwritten
        )
        
    except Exception as e:
        logger.error(f"Error applying schedule template: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to apply schedule template: {str(e)}"
        ) 