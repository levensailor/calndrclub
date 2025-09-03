from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import datetime

from core.database import database
from core.security import get_current_user
from core.logging import logger
from db.models import reminders
from schemas.reminder import ReminderCreate, ReminderUpdate, ReminderResponse

router = APIRouter()

@router.get("/", response_model=List[ReminderResponse])
async def get_reminders(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    current_user = Depends(get_current_user)
):
    try:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    query = reminders.select().where(
        (reminders.c.family_id == current_user['family_id']) &
        (reminders.c.date.between(start_date_obj, end_date_obj))
    ).order_by(reminders.c.date)
    
    reminder_records = await database.fetch_all(query)
    
    return [
        ReminderResponse(
            id=record['id'],
            date=str(record['date']),
            text=record['text'],
            notification_enabled=record['notification_enabled'],
            notification_time=str(record['notification_time']) if record['notification_time'] else None,
            created_at=str(record['created_at']),
            updated_at=str(record['updated_at'])
        ) for record in reminder_records
    ]
