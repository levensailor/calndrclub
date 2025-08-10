from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, date, time
import re

class MedicationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Medication name")
    dosage: Optional[str] = Field(None, max_length=100, description="Dosage information")
    frequency: Optional[str] = Field(None, max_length=100, description="Frequency of administration")
    instructions: Optional[str] = Field(None, description="Administration instructions")
    start_date: Optional[date] = Field(None, description="Start date for medication")
    end_date: Optional[date] = Field(None, description="End date for medication")
    is_active: bool = Field(True, description="Whether medication is currently active")
    reminder_enabled: bool = Field(False, description="Whether reminders are enabled")
    reminder_time: Optional[time] = Field(None, description="Time for daily reminders")
    notes: Optional[str] = Field(None, description="Additional notes")

    @validator('end_date')
    def validate_date_range(cls, v, values):
        if v is not None and 'start_date' in values and values['start_date'] is not None:
            if v < values['start_date']:
                raise ValueError('End date must be after start date')
        return v

    @validator('reminder_time')
    def validate_reminder_time(cls, v, values):
        if v is not None and 'reminder_enabled' in values and not values['reminder_enabled']:
            raise ValueError('Reminder time can only be set when reminders are enabled')
        return v

class MedicationCreate(MedicationBase):
    # family_id is set automatically from current_user in the endpoint
    pass

class MedicationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    dosage: Optional[str] = Field(None, max_length=100)
    frequency: Optional[str] = Field(None, max_length=100)
    instructions: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None
    reminder_enabled: Optional[bool] = None
    reminder_time: Optional[time] = None
    notes: Optional[str] = None

    @validator('end_date')
    def validate_date_range(cls, v, values):
        if v is not None and 'start_date' in values and values['start_date'] is not None:
            if v < values['start_date']:
                raise ValueError('End date must be after start date')
        return v

    @validator('reminder_time')
    def validate_reminder_time(cls, v, values):
        if v is not None and 'reminder_enabled' in values and not values['reminder_enabled']:
            raise ValueError('Reminder time can only be set when reminders are enabled')
        return v

class MedicationResponse(MedicationBase):
    id: int
    family_id: str
    created_at: str  # Changed to string for consistency with frontend expectations
    updated_at: str  # Changed to string for consistency with frontend expectations
    next_reminder: Optional[datetime] = Field(None, description="Next reminder time")

    class Config:
        from_attributes = True

class MedicationListParams(BaseModel):
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    reminder_enabled: Optional[bool] = Field(None, description="Filter by reminder enabled")
    page: Optional[int] = Field(1, ge=1, description="Page number")
    limit: Optional[int] = Field(20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field("name", description="Sort by: name, start_date, created_at")
    sort_order: Optional[str] = Field("asc", description="Sort order: asc, desc")

class MedicationListResponse(BaseModel):
    medications: List[MedicationResponse]
    total: int
    page: int
    limit: int
    total_pages: int

class MedicationReminderResponse(BaseModel):
    id: int
    name: str
    dosage: Optional[str]
    frequency: Optional[str]
    reminder_time: time
    next_reminder: datetime
    is_active: bool

    class Config:
        from_attributes = True

class MedicationReminderListResponse(BaseModel):
    reminders: List[MedicationReminderResponse]
    total: int 


# --- Presets ---

class MedicationPreset(BaseModel):
    name: str
    common_dosages: List[str]
    common_frequencies: List[str]
    default_dosage: Optional[str] = None
    default_frequency: Optional[str] = None
    aliases: Optional[List[str]] = None

class MedicationPresetListResponse(BaseModel):
    presets: List[MedicationPreset]