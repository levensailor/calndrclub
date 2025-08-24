from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

class CoparentInfoRequest(BaseModel):
    """Schema for coparent information submission."""
    coparent_first_name: str = Field(..., min_length=1, max_length=50, description="Coparent's first name")

class ChildInfoRequest(BaseModel):
    """Schema for child information submission."""
    first_name: str = Field(..., min_length=1, max_length=50, description="Child's first name")
    last_name: str = Field(..., min_length=1, max_length=50, description="Child's last name")
    date_of_birth: str = Field(..., description="Child's date of birth in YYYY-MM-DD format")

class CustodyScheduleRequest(BaseModel):
    """Schema for custody schedule submission."""
    schedule_type: str = Field(..., description="Type of custody schedule (e.g., 'weekly', 'biweekly', 'custom')")
    schedule_details: dict = Field(..., description="Schedule details as JSON object")

class EnrollmentStatusResponse(BaseModel):
    """Schema for enrollment status response."""
    enrolled: bool
    coparent_enrolled: bool
    coparent_invited: bool
    next_step: Optional[str] = None
    family_id: Optional[str] = None

class EnrollmentStepResponse(BaseModel):
    """Schema for enrollment step completion response."""
    success: bool
    message: str
    next_step: Optional[str] = None
