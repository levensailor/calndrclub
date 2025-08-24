from typing import Optional
from pydantic import BaseModel, EmailStr

class Token(BaseModel):
    """Token schema for authentication responses."""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Token data for validating JWT tokens."""
    sub: Optional[str] = None

class LoginAfterVerificationRequest(BaseModel):
    """Schema for login after email verification request."""
    email: EmailStr
