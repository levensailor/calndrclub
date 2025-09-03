import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from backend.core.database import database
from backend.core.security import get_current_user, uuid_to_string
from backend.core.logging import logger
from backend.db.models import children
from backend.schemas.child import ChildCreate, ChildResponse

router = APIRouter()

@router.get("/", response_model=List[ChildResponse])
async def get_children(current_user = Depends(get_current_user)):
    """
    Get all children for the current user's family.
    """
    query = children.select().where(
        children.c.family_id == current_user['family_id']
    ).order_by(children.c.dob.desc())  # Newest first
    
    child_records = await database.fetch_all(query)
    
    return [
        ChildResponse(
            id=uuid_to_string(record['id']),
            first_name=record['first_name'],
            last_name=record['last_name'],
            dob=str(record['dob']),
            family_id=uuid_to_string(record['family_id'])
        )
        for record in child_records
    ]

@router.post("/", response_model=ChildResponse)
async def create_child(child_data: ChildCreate, current_user = Depends(get_current_user)):
    """
    Create a new child for the current user's family.
    """
    try:
        # Parse the date string
        dob_date = datetime.strptime(child_data.dob, '%Y-%m-%d').date()
        
        # Generate UUID for new child
        child_id = uuid.uuid4()
        
        # Insert child
        child_insert = children.insert().values(
            id=child_id,
            family_id=current_user['family_id'],
            first_name=child_data.first_name,
            last_name=child_data.last_name,
            dob=dob_date
        )
        await database.execute(child_insert)
        
        # Fetch the created child
        child_record = await database.fetch_one(children.select().where(children.c.id == child_id))
        
        return ChildResponse(
            id=uuid_to_string(child_record['id']),
            first_name=child_record['first_name'],
            last_name=child_record['last_name'],
            dob=str(child_record['dob']),
            family_id=uuid_to_string(child_record['family_id'])
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        logger.error(f"Error creating child: {e}")
        raise HTTPException(status_code=500, detail="Failed to create child")

@router.put("/{child_id}", response_model=ChildResponse)
async def update_child(child_id: str, child_data: ChildCreate, current_user = Depends(get_current_user)):
    """
    Update a child that belongs to the current user's family.
    """
    try:
        # Parse child_id as UUID
        child_uuid = uuid.UUID(child_id)
        
        # Check if child belongs to user's family
        check_query = children.select().where(
            (children.c.id == child_uuid) & 
            (children.c.family_id == current_user['family_id'])
        )
        existing = await database.fetch_one(check_query)
        if not existing:
            raise HTTPException(status_code=404, detail="Child not found")
        
        # Parse the date string
        dob_date = datetime.strptime(child_data.dob, '%Y-%m-%d').date()
        
        # Update child
        update_query = children.update().where(children.c.id == child_uuid).values(
            first_name=child_data.first_name,
            last_name=child_data.last_name,
            dob=dob_date
        )
        await database.execute(update_query)
        
        # Fetch updated record
        child_record = await database.fetch_one(children.select().where(children.c.id == child_uuid))
        
        return ChildResponse(
            id=uuid_to_string(child_record['id']),
            first_name=child_record['first_name'],
            last_name=child_record['last_name'],
            dob=str(child_record['dob']),
            family_id=uuid_to_string(child_record['family_id'])
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid child ID or date format")
    except Exception as e:
        logger.error(f"Error updating child: {e}")
        raise HTTPException(status_code=500, detail="Failed to update child")

@router.delete("/{child_id}")
async def delete_child(child_id: str, current_user = Depends(get_current_user)):
    """
    Delete a child from the current user's family.
    """
    try:
        # Parse child_id as UUID
        child_uuid = uuid.UUID(child_id)
        
        # Check if child belongs to user's family
        check_query = children.select().where(
            (children.c.id == child_uuid) & 
            (children.c.family_id == current_user['family_id'])
        )
        existing = await database.fetch_one(check_query)
        if not existing:
            raise HTTPException(status_code=404, detail="Child not found")
        
        # Delete the child
        delete_query = children.delete().where(children.c.id == child_uuid)
        await database.execute(delete_query)
        
        return {"status": "success", "message": "Child deleted successfully"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid child ID format")
    except Exception as e:
        logger.error(f"Error deleting child: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete child")
