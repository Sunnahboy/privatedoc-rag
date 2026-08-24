from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Any
from datetime import datetime

class ChatMessageBase(BaseModel):
    role: str
    content: str
    citations: Optional[List[Any]] = []

class ChatMessageResponse(ChatMessageBase):
    id: str
    session_id: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ChatSessionResponse(BaseModel):
    id: str
    title: Optional[str]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)