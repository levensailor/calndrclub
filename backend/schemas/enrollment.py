from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

from backend.schemas.base import BaseSchema

class EnrollmentCodeCreate(BaseModel):
    """Schema for creating an enrollment code."""
    coparent_first_name: Optional[str] = None
    coparent_last_name: Optional[str] = None
    coparent_email: Optional[str] = None
    coparent_phone: Optional[str] = None

class EnrollmentCodeResponse(BaseModel):
    """Schema for enrollment code response."""
    success: bool = True
    message: Optional[str] = None
    enrollmentCode: Optional[str] = None
    familyId: Optional[str] = None

class EnrollmentCodeValidate(BaseModel):
    """Schema for validating an enrollment code."""
    code: str = Field(..., min_length=6, max_length=6)

class EnrollmentCode(BaseSchema):
    """Schema for enrollment code."""
    id: int
    family_id: str
    code: str
    created_by_user_id: str
    coparent_first_name: Optional[str] = None
    coparent_last_name: Optional[str] = None
    coparent_email: Optional[str] = None
    coparent_phone: Optional[str] = None
    invitation_sent: bool = False
    invitation_sent_at: Optional[datetime] = None
    created_at: datetime

class EnrollmentInvite(BaseModel):
    """Schema for sending an enrollment invitation."""
    code: str
    coparent_first_name: str
    coparent_last_name: str
    coparent_email: str
    coparent_phone: Optional[str] = None