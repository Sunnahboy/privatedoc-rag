from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List
import uuid
from fastapi import HTTPException
from sqlalchemy import delete
# Import your async get_db generator
from app.database import get_db 
from app.models.chat import ChatSession, ChatMessage
from app.schemas.chat_schema import ChatSessionResponse, ChatMessageResponse

router = APIRouter(prefix="/chat", tags=["Chat History"])

@router.post("/sessions", response_model=ChatSessionResponse)
async def create_session(title: str = "New RAG Session", db: AsyncSession = Depends(get_db)):
    """Creates a new isolated chat session (Asynchronous)."""
    session_id = str(uuid.uuid4())
    new_session = ChatSession(id=session_id, title=title)
    
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    
    return new_session

@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_recent_messages(session_id: str, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """
    SLIDING WINDOW: Only fetches the 'limit' most recent messages.
    Uses SQLAlchemy 2.0 async select statements.
    """
    #Build the query
    stmt = select(ChatMessage)\
        .filter(ChatMessage.session_id == session_id)\
        .order_by(desc(ChatMessage.created_at))\
        .limit(limit)
    
    #Execute the async query
    result = await db.execute(stmt)
    
    #Extract the actual model objects
    messages = result.scalars().all()
    
    #oldest of the recent messages
    return messages[::-1]

@router.delete("/sessions/{session_id}/messages/{message_id}")
async def truncate_chat_history(session_id: str, message_id: str, db: AsyncSession = Depends(get_db)):
    """Deletes a specific message and all subsequent messages to handle inline edits."""
    
    #Find the exact message the user is editing to get its timestamp
    stmt = select(ChatMessage).filter(
        ChatMessage.session_id == session_id,
        ChatMessage.id == message_id
    )
    result = await db.execute(stmt)
    target_msg = result.scalars().first()

    if not target_msg:
        raise HTTPException(status_code=404, detail="Message not found")

    #Delete it and everything created after it in this session
    delete_stmt = delete(ChatMessage).filter(
        ChatMessage.session_id == session_id,
        ChatMessage.created_at >= target_msg.created_at
    )
    
    await db.execute(delete_stmt)
    await db.commit()

    return {"status": "success", "message": "History truncated."}