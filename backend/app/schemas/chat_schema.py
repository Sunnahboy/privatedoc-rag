from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Any
from datetime import datetime

class ChatMessageBase(BaseModel):
    role: str
    content: str
    citations: Optional[List[Any]] = []
    # THE FIX: status was missing here, so every /messages response silently
    # dropped it. The frontend's reconnect-on-mount logic depends on knowing
    # whether the last assistant message is still "queued"/"processing" -
    # without this field it always looked "completed" and never reconnected.
    status: Optional[str] = "completed"

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