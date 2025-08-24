from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class EmailVerificationRequest(BaseModel):
    """Schema for requesting email verification code"""
    email: EmailStr = Field(..., description="Email address to verify")

class EmailVerificationConfirm(BaseModel):
    """Schema for confirming email verification code"""
    email: EmailStr = Field(..., description="Email address being verified")
    code: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")

class EmailVerificationResponse(BaseModel):
    """Schema for email verification API responses"""
    success: bool
    message: str
    expires_in: Optional[int] = None  # Seconds until expiration
    user_id: Optional[str] = None  # Only returned on successful verification

class EmailVerificationInfo(BaseModel):
    """Schema for email verification record information"""
    id: int
    user_id: str
    email: str
    code: str
    expires_at: datetime
    is_verified: bool
    verified_at: Optional[datetime] = None
    attempts: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
