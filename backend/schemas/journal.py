from pydantic import BaseModel, field_validator, ValidationInfo
from typing import Optional, Union
from datetime import date, datetime, time
from uuid import UUID

class JournalEntryBase(BaseModel):
    title: Optional[str] = None
    content: str
    entry_date: date

class JournalEntryCreate(JournalEntryBase):
    pass

class JournalEntryUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    entry_date: Optional[date] = None

class JournalEntry(JournalEntryBase):
    id: int
    family_id: str
    user_id: str
    author_name: str  # Will be populated from user data
    created_at: datetime
    updated_at: datetime

    @field_validator('family_id', 'user_id', mode='before')
    @classmethod
    def uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    @field_validator('created_at', 'updated_at', mode='before')
    @classmethod
    def set_default_datetime(cls, v: Optional[datetime], info: ValidationInfo) -> datetime:
        if v is None:
            if info.data and 'entry_date' in info.data and info.data['entry_date']:
                return datetime.combine(info.data['entry_date'], time.min)
            return datetime.now()
        return v

    class Config:
        from_attributes = True 