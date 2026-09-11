import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.chat import ChatMessage, ChatSession
from app.schemas.chat_schema import (
    ChatMessageResponse,
    ChatSessionResponse,
    CreateSessionRequest,
    UpdateSessionRequest,
)

router = APIRouter(prefix="/chat", tags=["Chat History"])

# The linter ignores
DatabaseDep = Annotated[AsyncSession, Depends(get_db)]


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_session(
    request: CreateSessionRequest,
    db: DatabaseDep,
):
    """Creates a new isolated chat session (Asynchronous)."""
    session_id = str(uuid.uuid4())
    new_session = ChatSession(
        id=session_id,
        title="New Chat",
        scope_type=request.scope_type,
        document_ids=request.document_ids,
    )

    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)

    return new_session


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def get_all_sessions(db: DatabaseDep):
    """Returns all chat sessions for the Chat Focus sidebar, pinned first."""
    stmt = select(ChatSession).order_by(
        desc(ChatSession.is_pinned), desc(ChatSession.created_at)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.patch("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_session(
    session_id: str,
    request: UpdateSessionRequest,
    db: DatabaseDep,
):
    """Renames a session and/or toggles its pinned state."""
    session = await db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    if request.title is not None:
        trimmed = request.title.strip()
        session.title = trimmed or "New Chat"
    if request.is_pinned is not None:
        session.is_pinned = request.is_pinned

    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
async def get_recent_messages(
    session_id: str,
    db: DatabaseDep,
    limit: int = 100,
):
    """
    SLIDING WINDOW: Only fetches the 'limit' most recent messages.
    Uses SQLAlchemy 2.0 async select statements.
    """
    # Build the query
    # BUG FIX: user/assistant pairs share the same `created_at` timestamp
    # (inserted in the same commit), so `created_at` alone is not a stable
    # sort key - ties can be returned in either order. `seq` is a DB-assigned
    # autoincrementing column that always reflects true insertion order, so
    # it's used as the primary sort key to guarantee the assistant reply is
    # never ordered before its own user question.

    stmt = (
        select(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(desc(ChatMessage.seq))
        .limit(limit)
    )

    # Execute the async query
    result = await db.execute(stmt)

    # Extract the actual model objects
    messages = result.scalars().all()

    # oldest of the recent messages
    return messages[::-1]


@router.delete("/sessions/{session_id}/messages/{message_id}")
async def truncate_chat_history(session_id: str, message_id: str, db: DatabaseDep):
    """Deletes a specific message and all subsequent messages to handle inline edits."""

    # Find the exact message the user is editing to get its timestamp
    stmt = select(ChatMessage).filter(
        ChatMessage.session_id == session_id, ChatMessage.id == message_id
    )
    result = await db.execute(stmt)
    target_msg = result.scalars().first()

    if not target_msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Message not found"
        )

    # Delete it and everything created after it in this session
    delete_stmt = delete(ChatMessage).filter(
        ChatMessage.session_id == session_id,
        ChatMessage.created_at >= target_msg.created_at,
    )

    await db.execute(delete_stmt)
    await db.commit()

    return {"status": "success", "message": "History truncated."}
