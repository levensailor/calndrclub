"""
Medications API Endpoints
Handles CRUD operations for medications
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, date, time

from core.database import database
from core.security import get_current_user
from db.models import medications, users
from schemas.medication import (
    MedicationCreate,
    MedicationUpdate,
    MedicationResponse,
    MedicationListParams,
    MedicationListResponse,
    MedicationReminderResponse,
    MedicationReminderListResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_model=MedicationListResponse)
async def get_medications(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    reminder_enabled: Optional[bool] = Query(None, description="Filter by reminder enabled"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("name", description="Sort by: name, start_date, created_at"),
    sort_order: str = Query("asc", description="Sort order: asc, desc"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all medications for the authenticated family
    """
    try:
        # Build query
        query = medications.select().where(
            medications.c.family_id == current_user["family_id"]
        )
        
        # Apply filters
        if is_active is not None:
            query = query.where(medications.c.is_active == is_active)
        
        if reminder_enabled is not None:
            query = query.where(medications.c.reminder_enabled == reminder_enabled)
        
        # Get total count
        count_query = medications.select().where(
            medications.c.family_id == current_user["family_id"]
        )
        if is_active is not None:
            count_query = count_query.where(medications.c.is_active == is_active)
        if reminder_enabled is not None:
            count_query = count_query.where(medications.c.reminder_enabled == reminder_enabled)
        
        total = await database.fetch_val(
            f"SELECT COUNT(*) FROM medications WHERE family_id = '{current_user['family_id']}'" +
            (f" AND is_active = {is_active}" if is_active is not None else "") +
            (f" AND reminder_enabled = {reminder_enabled}" if reminder_enabled is not None else "")
        )
        total = total or 0
        
        # Apply sorting
        if sort_by == "name":
            order_column = medications.c.name
        elif sort_by == "start_date":
            order_column = medications.c.start_date
        elif sort_by == "created_at":
            order_column = medications.c.created_at
        else:
            order_column = medications.c.name
        
        if sort_order.lower() == "desc":
            query = query.order_by(order_column.desc())
        else:
            query = query.order_by(order_column.asc())
        
        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
        
        # Execute query
        medication_list = await database.fetch_all(query)
        
        # Convert to response format
        response_medications = []
        for med in medication_list:
            med_dict = dict(med)
            # Calculate next reminder time if reminder is enabled
            if med_dict.get("reminder_enabled") and med_dict.get("reminder_time"):
                # This would be calculated based on the reminder system
                med_dict["next_reminder"] = None  # TODO: Implement reminder calculation
            response_medications.append(MedicationResponse(**med_dict))
        
        total_pages = (total + limit - 1) // limit
        
        return MedicationListResponse(
            medications=response_medications,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )
        
    except Exception as e:
        logger.error(f"Error fetching medications: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/", response_model=MedicationResponse)
async def create_medication(
    medication_data: MedicationCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new medication
    """
    try:
        # Validate family ownership
        if medication_data.family_id != current_user["family_id"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Validate date range
        if medication_data.start_date and medication_data.end_date:
            if medication_data.end_date < medication_data.start_date:
                raise HTTPException(status_code=422, detail="End date must be after start date")
        
        # Validate reminder settings
        if medication_data.reminder_enabled and not medication_data.reminder_time:
            raise HTTPException(status_code=422, detail="Reminder time is required when reminders are enabled")
        
        # Prepare data
        medication_dict = medication_data.dict()
        medication_dict["created_at"] = datetime.now()
        medication_dict["updated_at"] = datetime.now()
        
        # Insert into database
        query = medications.insert().values(**medication_dict)
        medication_id = await database.execute(query)
        
        # Get the created medication
        created_medication = await database.fetch_one(
            medications.select().where(medications.c.id == medication_id)
        )
        
        med_dict = dict(created_medication)
        if med_dict.get("reminder_enabled") and med_dict.get("reminder_time"):
            med_dict["next_reminder"] = None  # TODO: Calculate next reminder
        
        return MedicationResponse(**med_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating medication: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{medication_id}", response_model=MedicationResponse)
async def get_medication(
    medication_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific medication
    """
    try:
        medication = await database.fetch_one(
            medications.select().where(
                and_(
                    medications.c.id == medication_id,
                    medications.c.family_id == current_user["family_id"]
                )
            )
        )
        
        if not medication:
            raise HTTPException(status_code=404, detail="Medication not found")
        
        med_dict = dict(medication)
        if med_dict.get("reminder_enabled") and med_dict.get("reminder_time"):
            med_dict["next_reminder"] = None  # TODO: Calculate next reminder
        
        return MedicationResponse(**med_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching medication: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{medication_id}", response_model=MedicationResponse)
async def update_medication(
    medication_id: int,
    medication_data: MedicationUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update a medication
    """
    try:
        # Check if medication exists and belongs to family
        existing_medication = await database.fetch_one(
            medications.select().where(
                and_(
                    medications.c.id == medication_id,
                    medications.c.family_id == current_user["family_id"]
                )
            )
        )
        
        if not existing_medication:
            raise HTTPException(status_code=404, detail="Medication not found")
        
        # Prepare update data
        update_data = medication_data.dict(exclude_unset=True)
        
        # Validate date range if both dates are provided
        if update_data.get("start_date") and update_data.get("end_date"):
            if update_data["end_date"] < update_data["start_date"]:
                raise HTTPException(status_code=422, detail="End date must be after start date")
        
        # Validate reminder settings
        if update_data.get("reminder_enabled") and not update_data.get("reminder_time"):
            raise HTTPException(status_code=422, detail="Reminder time is required when reminders are enabled")
        
        # Set updated timestamp
        update_data["updated_at"] = datetime.now()
        
        # Update database
        await database.execute(
            medications.update().where(
                medications.c.id == medication_id
            ).values(**update_data)
        )
        
        # Get updated medication
        updated_medication = await database.fetch_one(
            medications.select().where(medications.c.id == medication_id)
        )
        
        med_dict = dict(updated_medication)
        if med_dict.get("reminder_enabled") and med_dict.get("reminder_time"):
            med_dict["next_reminder"] = None  # TODO: Calculate next reminder
        
        return MedicationResponse(**med_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating medication: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{medication_id}")
async def delete_medication(
    medication_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a medication
    """
    try:
        # Check if medication exists and belongs to family
        existing_medication = await database.fetch_one(
            medications.select().where(
                and_(
                    medications.c.id == medication_id,
                    medications.c.family_id == current_user["family_id"]
                )
            )
        )
        
        if not existing_medication:
            raise HTTPException(status_code=404, detail="Medication not found")
        
        # TODO: Cancel associated reminders
        
        # Delete from database
        await database.execute(
            medications.delete().where(
                medications.c.id == medication_id
            )
        )
        
        return {"success": True, "message": "Medication deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting medication: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/active", response_model=MedicationListResponse)
async def get_active_medications(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get only active medications for the authenticated family
    """
    try:
        today = date.today()
        
        # Build query for active medications
        query = medications.select().where(
            and_(
                medications.c.family_id == current_user["family_id"],
                medications.c.is_active == True,
                or_(
                    medications.c.start_date.is_(None),
                    medications.c.start_date <= today
                ),
                or_(
                    medications.c.end_date.is_(None),
                    medications.c.end_date >= today
                )
            )
        )
        
        # Get total count
        total = await database.fetch_val(
            f"SELECT COUNT(*) FROM medications WHERE family_id = '{current_user['family_id']}' AND is_active = true" +
            f" AND (start_date IS NULL OR start_date <= '{today}')" +
            f" AND (end_date IS NULL OR end_date >= '{today}')"
        )
        total = total or 0
        
        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
        
        # Execute query
        medication_list = await database.fetch_all(query)
        
        # Convert to response format
        response_medications = []
        for med in medication_list:
            med_dict = dict(med)
            if med_dict.get("reminder_enabled") and med_dict.get("reminder_time"):
                med_dict["next_reminder"] = None  # TODO: Calculate next reminder
            response_medications.append(MedicationResponse(**med_dict))
        
        total_pages = (total + limit - 1) // limit
        
        return MedicationListResponse(
            medications=response_medications,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )
        
    except Exception as e:
        logger.error(f"Error fetching active medications: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/reminders", response_model=MedicationReminderListResponse)
async def get_medication_reminders(
    current_user: dict = Depends(get_current_user)
):
    """
    Get medications with active reminders
    """
    try:
        # Get medications with reminders enabled
        medication_list = await database.fetch_all(
            medications.select().where(
                and_(
                    medications.c.family_id == current_user["family_id"],
                    medications.c.reminder_enabled == True,
                    medications.c.is_active == True,
                    medications.c.reminder_time.isnot(None)
                )
            )
        )
        
        # Convert to response format
        reminder_list = []
        for med in medication_list:
            med_dict = dict(med)
            reminder_data = {
                "id": med_dict["id"],
                "name": med_dict["name"],
                "dosage": med_dict["dosage"],
                "frequency": med_dict["frequency"],
                "reminder_time": med_dict["reminder_time"],
                "next_reminder": None,  # TODO: Calculate next reminder
                "is_active": med_dict["is_active"]
            }
            reminder_list.append(MedicationReminderResponse(**reminder_data))
        
        return MedicationReminderListResponse(
            reminders=reminder_list,
            total=len(reminder_list)
        )
        
    except Exception as e:
        logger.error(f"Error fetching medication reminders: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") 