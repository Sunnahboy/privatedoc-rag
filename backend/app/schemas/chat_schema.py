from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.chat import ChatScope


class CreateSessionRequest(BaseModel):
    scope_type: ChatScope = ChatScope.ALL_DOCUMENTS
    document_ids: list[str] = []


class UpdateSessionRequest(BaseModel):
    """Partial update for a chat session - only provided fields are changed."""

    title: str | None = None
    is_pinned: bool | None = None


# The Incoming Request (What the frontend POSTs to FastAPI)
class ChatMessageRequest(BaseModel):
    session_id: str
    question: str
    document_ids: list[str] = Field(
        default=[], description="List of document IDs to search across"
    )


class ChatMessageBase(BaseModel):
    role: str
    content: str
    citations: list[Any] | None = []
    # THE FIX: status was missing here, so every /messages response silently
    # dropped it. The frontend's reconnect-on-mount logic depends on knowing
    # whether the last assistant message is still "queued"/"processing" -
    # without this field it always looked "completed" and never reconnected.
    status: str | None = "completed"
    # Track which documents were active for this specific turn
    document_ids: list[str] | None = []


class ChatMessageResponse(ChatMessageBase):
    id: str
    session_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSessionResponse(BaseModel):
    id: str
    title: str | None
    scope_type: ChatScope
    document_ids: list[str]
    is_pinned: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
