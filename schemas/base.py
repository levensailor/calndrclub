from typing import Optional
from pydantic import BaseModel

class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True
