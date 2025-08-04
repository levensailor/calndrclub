from typing import Optional
from pydantic import BaseModel

class Token(BaseModel):
    """Token schema for authentication responses."""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Token data for validating JWT tokens."""
    sub: Optional[str] = None
