from fastapi import APIRouter, Depends, HTTPException
from typing import List

from core.database import database
from core.security import get_current_user
from core.logging import logger
from db.models import babysitters, babysitter_families
from schemas.babysitter import BabysitterCreate, BabysitterResponse

router = APIRouter()

@router.get("", response_model=List[BabysitterResponse])
async def get_babysitters(current_user = Depends(get_current_user)):
    """
    Get all babysitters associated with the current user's family.
    """
    # Use SQLAlchemy query syntax instead of raw SQL
    query = babysitters.select().select_from(
        babysitters.join(babysitter_families, babysitters.c.id == babysitter_families.c.babysitter_id)
    ).where(
        babysitter_families.c.family_id == current_user['family_id']
    ).order_by(babysitters.c.first_name, babysitters.c.last_name)
    
    babysitter_records = await database.fetch_all(query)
    
    return [
        BabysitterResponse(
            id=record['id'],
            first_name=record['first_name'],
            last_name=record['last_name'],
            phone_number=record['phone_number'],
            rate=float(record['rate']) if record['rate'] else None,
            notes=record['notes'],
            created_by_user_id=str(record['created_by_user_id']),
            created_at=str(record['created_at'])
        )
        for record in babysitter_records
    ]

@router.post("", response_model=BabysitterResponse)
async def create_babysitter(babysitter_data: BabysitterCreate, current_user = Depends(get_current_user)):
    """
    Create a new babysitter and associate with the current user's family.
    """
    try:
        # Insert babysitter
        babysitter_insert = babysitters.insert().values(
            first_name=babysitter_data.first_name,
            last_name=babysitter_data.last_name,
            phone_number=babysitter_data.phone_number,
            rate=babysitter_data.rate,
            notes=babysitter_data.notes,
            created_by_user_id=current_user['id']
        )
        babysitter_id = await database.execute(babysitter_insert)
        
        # Associate with family
        family_insert = babysitter_families.insert().values(
            babysitter_id=babysitter_id,
            family_id=current_user['family_id'],
            added_by_user_id=current_user['id']
        )
        await database.execute(family_insert)
        
        # Fetch the created babysitter
        babysitter_record = await database.fetch_one(babysitters.select().where(babysitters.c.id == babysitter_id))
        
        return BabysitterResponse(
            id=babysitter_record['id'],
            first_name=babysitter_record['first_name'],
            last_name=babysitter_record['last_name'],
            phone_number=babysitter_record['phone_number'],
            rate=float(babysitter_record['rate']) if babysitter_record['rate'] else None,
            notes=babysitter_record['notes'],
            created_by_user_id=str(babysitter_record['created_by_user_id']),
            created_at=str(babysitter_record['created_at'])
        )
    except Exception as e:
        logger.error(f"Error creating babysitter: {e}")
        raise HTTPException(status_code=500, detail="Failed to create babysitter")

@router.put("/{babysitter_id}", response_model=BabysitterResponse)
async def update_babysitter(babysitter_id: int, babysitter_data: BabysitterCreate, current_user = Depends(get_current_user)):
    """
    Update a babysitter that belongs to the current user's family.
    """
    # Check if babysitter belongs to user's family using SQLAlchemy syntax
    check_query = babysitters.select().select_from(
        babysitters.join(babysitter_families, babysitters.c.id == babysitter_families.c.babysitter_id)
    ).where(
        (babysitters.c.id == babysitter_id) & 
        (babysitter_families.c.family_id == current_user['family_id'])
    )
    existing = await database.fetch_one(check_query)
    if not existing:
        raise HTTPException(status_code=404, detail="Babysitter not found")
    
    # Update babysitter
    update_query = babysitters.update().where(babysitters.c.id == babysitter_id).values(
        first_name=babysitter_data.first_name,
        last_name=babysitter_data.last_name,
        phone_number=babysitter_data.phone_number,
        rate=babysitter_data.rate,
        notes=babysitter_data.notes
    )
    await database.execute(update_query)
    
    # Fetch updated record
    babysitter_record = await database.fetch_one(babysitters.select().where(babysitters.c.id == babysitter_id))
    
    return BabysitterResponse(
        id=babysitter_record['id'],
        first_name=babysitter_record['first_name'],
        last_name=babysitter_record['last_name'],
        phone_number=babysitter_record['phone_number'],
        rate=float(babysitter_record['rate']) if babysitter_record['rate'] else None,
        notes=babysitter_record['notes'],
        created_by_user_id=str(babysitter_record['created_by_user_id']),
        created_at=str(babysitter_record['created_at'])
    )

@router.delete("/{babysitter_id}")
async def delete_babysitter(babysitter_id: int, current_user = Depends(get_current_user)):
    """
    Remove a babysitter from the current user's family (deletes the association, not the babysitter).
    """
    # Delete the family association
    delete_query = babysitter_families.delete().where(
        (babysitter_families.c.babysitter_id == babysitter_id) &
        (babysitter_families.c.family_id == current_user['family_id'])
    )
    result = await database.execute(delete_query)
    
    if result == 0:
        raise HTTPException(status_code=404, detail="Babysitter not found in your family")
    
    return {"status": "success", "message": "Babysitter removed from family"}
