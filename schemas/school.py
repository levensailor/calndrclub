from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

class SchoolProviderCreate(BaseModel):
    name: str
    address: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    hours: Optional[str] = None
    notes: Optional[str] = None
    google_place_id: Optional[str] = None
    rating: Optional[float] = None
    website: Optional[str] = None

class SchoolProviderResponse(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    hours: Optional[str] = None
    notes: Optional[str] = None
    google_place_id: Optional[str] = None
    rating: Optional[float] = None
    website: Optional[str] = None
    created_by_user_id: str
    created_at: str
    updated_at: str

class SchoolSearchRequest(BaseModel):
    location_type: str  # "current" or "zipcode"
    zipcode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius: Optional[int] = 5000  # meters, default 5km

class SchoolSearchResult(BaseModel):
    place_id: str
    name: str
    address: str
    phone_number: Optional[str] = None
    rating: Optional[float] = None
    website: Optional[str] = None
    hours: Optional[str] = None
    distance: Optional[float] = None  # distance in meters 

class SchoolCalendarSync(BaseModel):
    id: Optional[int] = None
    school_provider_id: int
    calendar_url: str
    last_sync_at: Optional[datetime] = None
    last_sync_success: Optional[bool] = None
    last_sync_error: Optional[str] = None
    events_count: Optional[int] = 0
    sync_enabled: Optional[bool] = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# School Event schemas
class SchoolEventBase(BaseModel):
    event_date: datetime
    title: str
    description: Optional[str] = None
    event_type: Optional[str] = None  # holiday, closure, early_dismissal, event, etc.
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    all_day: bool = False

class SchoolEventCreate(SchoolEventBase):
    school_provider_id: int

class SchoolEventUpdate(BaseModel):
    event_date: Optional[datetime] = None
    title: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    all_day: Optional[bool] = None

class SchoolEvent(SchoolEventBase):
    id: int
    school_provider_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SchoolEventBulkCreate(BaseModel):
    school_provider_id: int
    events: List[SchoolEventBase]

class SchoolEventBulkResponse(BaseModel):
    created: int
    updated: int
    errors: List[str] = [] 