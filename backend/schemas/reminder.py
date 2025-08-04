from typing import Optional
from pydantic import BaseModel

class ReminderCreate(BaseModel):
    date: str  # Date string in YYYY-MM-DD format
    text: str
    notification_enabled: bool = False
    notification_time: Optional[str] = None  # Time string in HH:MM format

class ReminderUpdate(BaseModel):
    text: str
    notification_enabled: bool = False
    notification_time: Optional[str] = None  # Time string in HH:MM format

class ReminderResponse(BaseModel):
    id: int
    date: str  # Date string in YYYY-MM-DD format
    text: str
    notification_enabled: bool
    notification_time: Optional[str] = None  # Time string in HH:MM format
    created_at: str
    updated_at: str
