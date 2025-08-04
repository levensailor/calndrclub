from typing import Optional
from pydantic import BaseModel

class ChildCreate(BaseModel):
    first_name: str
    last_name: str
    dob: str  # Date string in YYYY-MM-DD format

class ChildResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    dob: str  # Date string in YYYY-MM-DD format
    family_id: str
