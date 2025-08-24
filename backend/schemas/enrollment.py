from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class EnrollmentCodeCreate(BaseModel):
    """Schema for creating an enrollment code"""
    pass  # No input needed, code is generated automatically

class EnrollmentCodeValidate(BaseModel):
    """Schema for validating an enrollment code"""
    code: str = Field(..., min_length=6, max_length=6, description="6-character enrollment code")

class EnrollmentCodeResponse(BaseModel):
    """Schema for enrollment code API responses"""
    success: bool
    message: Optional[str] = None
    enrollment_code: Optional[str] = None
    family_id: Optional[int] = None

class EnrollmentCodeInfo(BaseModel):
    """Schema for enrollment code information"""
    id: int
    code: str
    family_id: int
    created_by_user_id: int
    is_used: bool
    used_by_user_id: Optional[int] = None
    expires_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
