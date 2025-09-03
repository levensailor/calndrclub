from typing import Optional, List
from pydantic import BaseModel
from schemas.base import BaseSchema
import uuid

class FamilyBase(BaseSchema):
    """Base schema for family data."""
    name: str

class FamilyCreate(FamilyBase):
    """Schema for creating a new family."""
    pass

class FamilyResponse(FamilyBase):
    """Schema for family response data."""
    id: str
    daycare_sync_id: Optional[int] = None
    school_sync_id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
