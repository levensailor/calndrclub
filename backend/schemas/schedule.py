from pydantic import BaseModel
from typing import Optional, Dict, Any
from enum import Enum

class SchedulePatternType(str, Enum):
    weekly = "weekly"
    alternating_weeks = "alternating_weeks"
    alternating_days = "alternating_days"
    custom = "custom"

class WeeklySchedulePattern(BaseModel):
    sunday: Optional[str] = None
    monday: Optional[str] = None
    tuesday: Optional[str] = None
    wednesday: Optional[str] = None
    thursday: Optional[str] = None
    friday: Optional[str] = None
    saturday: Optional[str] = None

class AlternatingWeeksPattern(BaseModel):
    week_a_pattern: WeeklySchedulePattern
    week_b_pattern: WeeklySchedulePattern
    starting_week: str  # "A" or "B"
    reference_date: str  # ISO date string to determine which week is A/B

class ScheduleTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    pattern_type: SchedulePatternType
    weekly_pattern: Optional[WeeklySchedulePattern] = None
    alternating_weeks_pattern: Optional[AlternatingWeeksPattern] = None
    is_active: bool = True

    class Config:
        use_enum_values = True

class ScheduleTemplate(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    pattern_type: SchedulePatternType
    weekly_pattern: Optional[WeeklySchedulePattern] = None
    alternating_weeks_pattern: Optional[AlternatingWeeksPattern] = None
    is_active: bool
    family_id: str
    created_at: str
    updated_at: str

    class Config:
        use_enum_values = True

class ScheduleApplication(BaseModel):
    template_id: int
    start_date: str  # ISO date string
    end_date: str    # ISO date string
    overwrite_existing: bool = False

class ScheduleApplicationResponse(BaseModel):
    success: bool
    message: str
    days_applied: int
    conflicts_overwritten: Optional[int] = None 