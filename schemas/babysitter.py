from typing import Optional
from pydantic import BaseModel

class Babysitter(BaseModel):
    id: Optional[int] = None
    first_name: str
    last_name: str
    phone_number: str
    rate: Optional[float] = None
    notes: Optional[str] = None
    created_by_user_id: Optional[str] = None
    created_at: Optional[str] = None

class BabysitterCreate(BaseModel):
    first_name: str
    last_name: str
    phone_number: str
    rate: Optional[float] = None
    notes: Optional[str] = None

class BabysitterResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    phone_number: str
    rate: Optional[float] = None
    notes: Optional[str] = None
    created_by_user_id: str
    created_at: str
