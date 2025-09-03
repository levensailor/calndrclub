from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
import hashlib
import time

from core.database import database
from core.security import get_current_user
from core.logging import logger
from db.models import group_chats
from schemas.group_chat import GroupChatCreate

router = APIRouter()

@router.post("")
async def create_or_get_group_chat(chat_data: GroupChatCreate, current_user = Depends(get_current_user)):
    """
    Create a group chat identifier or return existing one for the given contact.
    This prevents duplicate group chats for the same contact.
    """
    # Check if group chat already exists
    existing_query = group_chats.select().where(
        (group_chats.c.family_id == current_user['family_id']) &
        (group_chats.c.contact_type == chat_data.contact_type) &
        (group_chats.c.contact_id == chat_data.contact_id)
    )
    existing_chat = await database.fetch_one(existing_query)
    
    if existing_chat:
        return {
            "group_identifier": existing_chat['group_identifier'],
            "exists": True,
            "created_at": str(existing_chat['created_at'])
        }
    
    # Create new group chat identifier
    # Generate unique group identifier
    unique_string = f"{current_user['family_id']}-{chat_data.contact_type}-{chat_data.contact_id}-{time.time()}"
    group_identifier = hashlib.md5(unique_string.encode()).hexdigest()[:16]
    
    try:
        insert_query = group_chats.insert().values(
            family_id=current_user['family_id'],
            contact_type=chat_data.contact_type,
            contact_id=chat_data.contact_id,
            group_identifier=group_identifier,
            created_by_user_id=current_user['id']
        )
        await database.execute(insert_query)
        
        return {
            "group_identifier": group_identifier,
            "exists": False,
            "created_at": str(datetime.now())
        }
    except Exception as e:
        logger.error(f"Error creating group chat: {e}")
        raise HTTPException(status_code=500, detail="Failed to create group chat")
