from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime

class ThemeBase(BaseModel):
    name: str
    mainBackgroundColor: str
    secondaryBackgroundColor: str
    textColor: str
    headerTextColor: str
    iconColor: str
    iconActiveColor: str
    accentColor: str
    parentOneColor: str
    parentTwoColor: str
    is_public: bool = False

class ThemeCreate(ThemeBase):
    pass

class ThemeUpdate(BaseModel):
    name: Optional[str] = None
    mainBackgroundColor: Optional[str] = None
    secondaryBackgroundColor: Optional[str] = None
    textColor: Optional[str] = None
    headerTextColor: Optional[str] = None
    iconColor: Optional[str] = None
    iconActiveColor: Optional[str] = None
    accentColor: Optional[str] = None
    parentOneColor: Optional[str] = None
    parentTwoColor: Optional[str] = None
    is_public: Optional[bool] = None

class Theme(ThemeBase):
    id: uuid.UUID
    created_by_user_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True 