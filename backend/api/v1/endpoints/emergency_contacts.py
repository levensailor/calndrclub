from fastapi import APIRouter, Depends, HTTPException
from typing import List

from backend.core.database import database
from backend.core.security import get_current_user
from backend.core.logging import logger
from backend.db.models import emergency_contacts
from backend.schemas.emergency_contact import EmergencyContactCreate, EmergencyContactResponse

router = APIRouter()

@router.get("", response_model=List[EmergencyContactResponse])
async def get_emergency_contacts(current_user = Depends(get_current_user)):
    """
    Get all emergency contacts for the current user's family.
    """
    query = emergency_contacts.select().where(
        emergency_contacts.c.family_id == current_user['family_id']
    ).order_by(emergency_contacts.c.first_name, emergency_contacts.c.last_name)
    
    contact_records = await database.fetch_all(query)
    
    return [
        EmergencyContactResponse(
            id=record['id'],
            first_name=record['first_name'],
            last_name=record['last_name'],
            phone_number=record['phone_number'],
            relationship=record['relationship'],
            notes=record['notes'],
            created_by_user_id=str(record['created_by_user_id']),
            created_at=str(record['created_at'])
        )
        for record in contact_records
    ]

@router.post("", response_model=EmergencyContactResponse)
async def create_emergency_contact(contact_data: EmergencyContactCreate, current_user = Depends(get_current_user)):
    """
    Create a new emergency contact for the current user's family.
    """
    try:
        insert_query = emergency_contacts.insert().values(
            family_id=current_user['family_id'],
            first_name=contact_data.first_name,
            last_name=contact_data.last_name,
            phone_number=contact_data.phone_number,
            relationship=contact_data.relationship,
            notes=contact_data.notes,
            created_by_user_id=current_user['id']
        )
        contact_id = await database.execute(insert_query)
        
        # Fetch the created contact
        contact_record = await database.fetch_one(emergency_contacts.select().where(emergency_contacts.c.id == contact_id))
        
        return EmergencyContactResponse(
            id=contact_record['id'],
            first_name=contact_record['first_name'],
            last_name=contact_record['last_name'],
            phone_number=contact_record['phone_number'],
            relationship=contact_record['relationship'],
            notes=contact_record['notes'],
            created_by_user_id=str(contact_record['created_by_user_id']),
            created_at=str(contact_record['created_at'])
        )
    except Exception as e:
        logger.error(f"Error creating emergency contact: {e}")
        raise HTTPException(status_code=500, detail="Failed to create emergency contact")

@router.put("/{contact_id}", response_model=EmergencyContactResponse)
async def update_emergency_contact(contact_id: int, contact_data: EmergencyContactCreate, current_user = Depends(get_current_user)):
    """
    Update an emergency contact that belongs to the current user's family.
    """
    # Check if contact belongs to user's family
    existing = await database.fetch_one(
        emergency_contacts.select().where(
            (emergency_contacts.c.id == contact_id) &
            (emergency_contacts.c.family_id == current_user['family_id'])
        )
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Emergency contact not found")
    
    # Update contact
    update_query = emergency_contacts.update().where(emergency_contacts.c.id == contact_id).values(
        first_name=contact_data.first_name,
        last_name=contact_data.last_name,
        phone_number=contact_data.phone_number,
        relationship=contact_data.relationship,
        notes=contact_data.notes
    )
    await database.execute(update_query)
    
    # Fetch updated record
    contact_record = await database.fetch_one(emergency_contacts.select().where(emergency_contacts.c.id == contact_id))
    
    return EmergencyContactResponse(
        id=contact_record['id'],
        first_name=contact_record['first_name'],
        last_name=contact_record['last_name'],
        phone_number=contact_record['phone_number'],
        relationship=contact_record['relationship'],
        notes=contact_record['notes'],
        created_by_user_id=str(contact_record['created_by_user_id']),
        created_at=str(contact_record['created_at'])
    )

@router.delete("/{contact_id}")
async def delete_emergency_contact(contact_id: int, current_user = Depends(get_current_user)):
    """
    Delete an emergency contact that belongs to the current user's family.
    """
    delete_query = emergency_contacts.delete().where(
        (emergency_contacts.c.id == contact_id) &
        (emergency_contacts.c.family_id == current_user['family_id'])
    )
    result = await database.execute(delete_query)
    
    if result == 0:
        raise HTTPException(status_code=404, detail="Emergency contact not found")
    
    return {"status": "success", "message": "Emergency contact deleted"}
