"""
Medications API Endpoints
Handles CRUD operations for medications
"""

import logging
from typing import List, Optional
import json
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
    MedicationReminderListResponse,
    MedicationPreset,
    MedicationPresetListResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _serialize_medication_row(row: dict) -> dict:
    """Normalize DB row values to match MedicationResponse schema types.

    - family_id: str
    - created_at/updated_at: str (ISO 8601)
    - next_reminder preserved if present
    """
    if row is None:
        return {}
    med = dict(row)
    # family_id may be UUID from DB driver
    if "family_id" in med and med["family_id"] is not None and not isinstance(med["family_id"], str):
        med["family_id"] = str(med["family_id"])
    # created_at/updated_at should be strings for iOS compatibility
    if "created_at" in med and med["created_at"] is not None:
        try:
            med["created_at"] = med["created_at"].isoformat()
        except Exception:
            med["created_at"] = str(med["created_at"])  # fallback
    if "updated_at" in med and med["updated_at"] is not None:
        try:
            med["updated_at"] = med["updated_at"].isoformat()
        except Exception:
            med["updated_at"] = str(med["updated_at"])  # fallback
    return med


def _kv_log(d: dict) -> str:
    """Create a JSON string of key -> {value, type} for safe logging."""
    try:
        serializable = {}
        for k, v in (d or {}).items():
            try:
                serializable[k] = {"value": str(v), "type": type(v).__name__}
            except Exception:
                serializable[k] = {"value": "<unrepr>", "type": type(v).__name__}
        return json.dumps(serializable, ensure_ascii=False)
    except Exception:
        return str(d)

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
            med_dict = _serialize_medication_row(med_dict)
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
        # Log incoming payload (as provided by client)
        try:
            incoming = medication_data.dict()
        except Exception:
            incoming = {}
        logger.info(
            "create_medication(): incoming payload kv: %s",
            _kv_log(incoming),
        )
        # Set family_id from current user (don't require it in request)
        medication_dict = medication_data.dict()
        medication_dict["family_id"] = current_user["family_id"]
        
        # Validate date range
        if medication_data.start_date and medication_data.end_date:
            if medication_data.end_date < medication_data.start_date:
                raise HTTPException(status_code=422, detail="End date must be after start date")
        
        # Validate reminder settings
        if medication_data.reminder_enabled and not medication_data.reminder_time:
            raise HTTPException(status_code=422, detail="Reminder time is required when reminders are enabled")
        
        # Prepare data with timestamps
        medication_dict["created_at"] = datetime.now()
        medication_dict["updated_at"] = datetime.now()
        
        # Log the finalized dict before DB insert
        logger.info(
            "create_medication(): final insert dict kv: %s",
            _kv_log(medication_dict),
        )

        # Insert into database
        query = medications.insert().values(**medication_dict)
        medication_id = await database.execute(query)
        
        # Get the created medication
        created_medication = await database.fetch_one(
            medications.select().where(medications.c.id == medication_id)
        )
        
        med_dict = dict(created_medication)
        logger.info(med_dict)
        if med_dict.get("reminder_enabled") and med_dict.get("reminder_time"):
            med_dict["next_reminder"] = None  # TODO: Calculate next reminder
        med_dict = _serialize_medication_row(med_dict)
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
        med_dict = _serialize_medication_row(med_dict)
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
        med_dict = _serialize_medication_row(med_dict)
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
            med_dict = _serialize_medication_row(med_dict)
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


@router.get("/presets", response_model=MedicationPresetListResponse)
async def get_medication_presets(current_user: dict = Depends(get_current_user)):
    """
    Returns a curated list of common pediatric medications with common dosages and frequencies.
    Also supports custom entries on the client side; this endpoint is for convenience presets only.
    """
    try:
        # These presets are intentionally static and opinionated for great UX.
        presets: list[MedicationPreset] = [
            MedicationPreset(
                name="Tylenol (Acetaminophen)",
                common_dosages=["80 mg", "160 mg", "240 mg", "320 mg", "500 mg"],
                common_frequencies=["Every 4 hours", "Every 6 hours", "Every 8 hours", "As needed"],
                default_dosage="160 mg",
                default_frequency="Every 6 hours",
                aliases=["Acetaminophen", "Paracetamol"]
            ),
            MedicationPreset(
                name="Motrin (Ibuprofen)",
                common_dosages=["50 mg", "100 mg", "200 mg", "400 mg"],
                common_frequencies=["Every 6 hours", "Every 8 hours", "As needed"],
                default_dosage="100 mg",
                default_frequency="Every 8 hours",
                aliases=["Ibuprofen", "Advil"]
            ),
            MedicationPreset(
                name="Zyrtec (Cetirizine)",
                common_dosages=["2.5 mg", "5 mg", "10 mg"],
                common_frequencies=["Once daily", "As needed"],
                default_dosage="5 mg",
                default_frequency="Once daily",
                aliases=["Cetirizine"]
            ),
            MedicationPreset(
                name="Benadryl (Diphenhydramine)",
                common_dosages=["6.25 mg", "12.5 mg", "25 mg"],
                common_frequencies=["Every 6 hours", "As needed"],
                default_dosage="12.5 mg",
                default_frequency="As needed",
                aliases=["Diphenhydramine"]
            ),
            MedicationPreset(
                name="Amoxicillin",
                common_dosages=["125 mg", "250 mg", "400 mg"],
                common_frequencies=["Twice daily", "Three times daily"],
                default_dosage="400 mg",
                default_frequency="Twice daily",
                aliases=[]
            ),
        ]

        return MedicationPresetListResponse(presets=presets)
    except Exception as e:
        logger.error(f"Error fetching medication presets: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")