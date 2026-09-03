from pydantic import BaseModel, ConfigDict,Field
from typing import List, Optional, Any
from datetime import datetime


#The Incoming Request (What the frontend POSTs to FastAPI)
class ChatMessageRequest(BaseModel):
    session_id: str
    question: str
    document_ids: List[str] = Field(min_length=1, description="List of document IDs to search across")
class ChatMessageBase(BaseModel):
    role: str
    content: str
    citations: Optional[List[Any]] = []
    # THE FIX: status was missing here, so every /messages response silently
    # dropped it. The frontend's reconnect-on-mount logic depends on knowing
    # whether the last assistant message is still "queued"/"processing" -
    # without this field it always looked "completed" and never reconnected.
    status: Optional[str] = "completed"
    #Track which documents were active for this specific turn
    document_ids: Optional[List[str]] = []

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