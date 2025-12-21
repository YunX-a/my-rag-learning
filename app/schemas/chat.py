from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Any

class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    sources: Optional[List[Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ConversationResponse(BaseModel):
    id: int
    title: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True