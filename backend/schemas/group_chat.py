from typing import Optional
from pydantic import BaseModel

class GroupChatCreate(BaseModel):
    contact_type: str  # 'babysitter' or 'emergency'
    contact_id: int
    group_identifier: Optional[str] = None
