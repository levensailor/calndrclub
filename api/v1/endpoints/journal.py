from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import date, datetime
from sqlalchemy import and_, or_, desc
import sqlalchemy

from core.database import database
from core.security import get_current_user
from core.logging import logger
from db.models import journal_entries, users
from schemas.journal import JournalEntry, JournalEntryCreate, JournalEntryUpdate

router = APIRouter()

@router.get("", response_model=List[JournalEntry])
async def get_journal_entries(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 50,
    current_user = Depends(get_current_user)
):
    """
    Get journal entries for the family, optionally filtered by date range
    """
    try:
        # Build the base query
        query = sqlalchemy.select(
            journal_entries.c.id,
            journal_entries.c.family_id,
            journal_entries.c.user_id,
            journal_entries.c.title,
            journal_entries.c.content,
            journal_entries.c.entry_date,
            journal_entries.c.created_at,
            journal_entries.c.updated_at,
            users.c.first_name,
            users.c.last_name
        ).select_from(
            journal_entries.join(users, journal_entries.c.user_id == users.c.id)
        )
        
        # Add filters
        conditions = [journal_entries.c.family_id == current_user['family_id']]
        if start_date:
            conditions.append(journal_entries.c.entry_date >= start_date)
        if end_date:
            conditions.append(journal_entries.c.entry_date <= end_date)
        
        query = query.where(and_(*conditions))
        
        # Add ordering and limit
        query = query.order_by(desc(journal_entries.c.entry_date), desc(journal_entries.c.created_at)).limit(limit)
        
        rows = await database.fetch_all(query)
        
        # Transform the results to include author name
        entries = []
        for row in rows:
            entry_dict = dict(row)
            entry_dict['author_name'] = f"{row['first_name']} {row['last_name']}"
            entries.append(JournalEntry(**entry_dict))
        
        logger.info(f"Fetched {len(entries)} journal entries for family {current_user['family_id']}")
        return entries
        
    except Exception as e:
        logger.error(f"Error fetching journal entries: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch journal entries")

@router.post("", response_model=JournalEntry)
async def create_journal_entry(
    entry_data: JournalEntryCreate,
    current_user = Depends(get_current_user)
):
    """
    Create a new journal entry
    """
    try:
        # Insert the journal entry
        insert_query = journal_entries.insert().values(
            family_id=current_user['family_id'],
            user_id=current_user['id'],
            title=entry_data.title,
            content=entry_data.content,
            entry_date=entry_data.entry_date
        )
        
        entry_id = await database.execute(insert_query)
        
        # Fetch the created entry with user info
        select_query = sqlalchemy.select(
            journal_entries.c.id,
            journal_entries.c.family_id,
            journal_entries.c.user_id,
            journal_entries.c.title,
            journal_entries.c.content,
            journal_entries.c.entry_date,
            journal_entries.c.created_at,
            journal_entries.c.updated_at,
            users.c.first_name,
            users.c.last_name
        ).select_from(
            journal_entries.join(users, journal_entries.c.user_id == users.c.id)
        ).where(journal_entries.c.id == entry_id)
        
        row = await database.fetch_one(select_query)
        if not row:
            raise HTTPException(status_code=404, detail="Created entry not found")
        
        # Transform the result
        entry_dict = dict(row)
        entry_dict['author_name'] = f"{row['first_name']} {row['last_name']}"
        
        logger.info(f"Created journal entry {entry_id} for family {current_user['family_id']}")
        return JournalEntry(**entry_dict)
        
    except Exception as e:
        logger.error(f"Error creating journal entry: {e}")
        raise HTTPException(status_code=500, detail="Failed to create journal entry")

@router.put("/{entry_id}", response_model=JournalEntry)
async def update_journal_entry(
    entry_id: int,
    entry_data: JournalEntryUpdate,
    current_user = Depends(get_current_user)
):
    """
    Update a journal entry (only the author can update their own entries)
    """
    try:
        # Check if entry exists and belongs to current user
        existing_query = journal_entries.select().where(
            and_(
                journal_entries.c.id == entry_id,
                journal_entries.c.family_id == current_user['family_id'],
                journal_entries.c.user_id == current_user['id']
            )
        )
        
        existing_entry = await database.fetch_one(existing_query)
        if not existing_entry:
            raise HTTPException(status_code=404, detail="Journal entry not found or access denied")
        
        # Build update data (only include fields that are not None)
        update_data = {}
        if entry_data.title is not None:
            update_data['title'] = entry_data.title
        if entry_data.content is not None:
            update_data['content'] = entry_data.content
        if entry_data.entry_date is not None:
            update_data['entry_date'] = entry_data.entry_date
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No data provided for update")
        
        # Update the entry
        update_query = (
            journal_entries.update()
            .where(journal_entries.c.id == entry_id)
            .values(**update_data)
        )
        
        await database.execute(update_query)
        
        # Fetch the updated entry with user info
        select_query = sqlalchemy.select(
            journal_entries.c.id,
            journal_entries.c.family_id,
            journal_entries.c.user_id,
            journal_entries.c.title,
            journal_entries.c.content,
            journal_entries.c.entry_date,
            journal_entries.c.created_at,
            journal_entries.c.updated_at,
            users.c.first_name,
            users.c.last_name
        ).select_from(
            journal_entries.join(users, journal_entries.c.user_id == users.c.id)
        ).where(journal_entries.c.id == entry_id)
        
        row = await database.fetch_one(select_query)
        entry_dict = dict(row)
        entry_dict['author_name'] = f"{row['first_name']} {row['last_name']}"
        
        logger.info(f"Updated journal entry {entry_id}")
        return JournalEntry(**entry_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating journal entry: {e}")
        raise HTTPException(status_code=500, detail="Failed to update journal entry")

@router.delete("/{entry_id}")
async def delete_journal_entry(
    entry_id: int,
    current_user = Depends(get_current_user)
):
    """
    Delete a journal entry (only the author can delete their own entries)
    """
    try:
        # Check if entry exists and belongs to current user
        existing_query = journal_entries.select().where(
            and_(
                journal_entries.c.id == entry_id,
                journal_entries.c.family_id == current_user['family_id'],
                journal_entries.c.user_id == current_user['id']
            )
        )
        
        existing_entry = await database.fetch_one(existing_query)
        if not existing_entry:
            raise HTTPException(status_code=404, detail="Journal entry not found or access denied")
        
        # Delete the entry
        delete_query = journal_entries.delete().where(journal_entries.c.id == entry_id)
        await database.execute(delete_query)
        
        logger.info(f"Deleted journal entry {entry_id}")
        return {"message": "Journal entry deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting journal entry: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete journal entry")

@router.get("/{entry_id}", response_model=JournalEntry)
async def get_journal_entry(
    entry_id: int,
    current_user = Depends(get_current_user)
):
    """
    Get a specific journal entry by ID
    """
    try:
        # Fetch the entry with user info
        select_query = sqlalchemy.select(
            journal_entries.c.id,
            journal_entries.c.family_id,
            journal_entries.c.user_id,
            journal_entries.c.title,
            journal_entries.c.content,
            journal_entries.c.entry_date,
            journal_entries.c.created_at,
            journal_entries.c.updated_at,
            users.c.first_name,
            users.c.last_name
        ).select_from(
            journal_entries.join(users, journal_entries.c.user_id == users.c.id)
        ).where(
            and_(
                journal_entries.c.id == entry_id,
                journal_entries.c.family_id == current_user['family_id']
            )
        )
        
        row = await database.fetch_one(select_query)
        if not row:
            raise HTTPException(status_code=404, detail="Journal entry not found")
        
        # Transform the result
        entry_dict = dict(row)
        entry_dict['author_name'] = f"{row['first_name']} {row['last_name']}"
        
        return JournalEntry(**entry_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching journal entry: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch journal entry") 