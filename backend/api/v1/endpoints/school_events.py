from fastapi import APIRouter, Depends, HTTPException

from core.security import get_current_user
from core.logging import logger
from services.school_events_service import fetch_school_events

router = APIRouter()

@router.get("/")
async def get_school_events():
    """Returns a JSON array of school events scraped from the Learning Tree website."""
    try:
        events = await fetch_school_events()
        return events
    except Exception as e:
        logger.error(f"Error retrieving school events: {e}")
        raise HTTPException(status_code=500, detail="Unable to retrieve school events")
