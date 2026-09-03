# app/models/chat.py
from sqlalchemy import Column, String, DateTime, JSON, Text, ForeignKey, Integer, Sequence
from sqlalchemy.sql import func
from app.database import Base

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    role = Column(String, nullable=False) # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    
    # Store which chunks/images the LLM used to answer this specific message
    citations = Column(JSON, default=[]) 
    # Store the active documents for this specific turn
    document_ids = Column(JSON, default=[], nullable=False)
    #track rabbitMQ worker
    status = Column(String, default="completed", nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # BUG FIX: user/assistant message pairs are inserted in the same commit and
    # can end up with an identical `created_at` timestamp (same transaction
    # time). Ordering solely by `created_at` is then non-deterministic and
    # Postgres can occasionally return the assistant reply BEFORE its own
    # user question, which silently misplaces the message in the UI and
    # looks exactly like a "blank/missing assistant bubble" bug. A DB-assigned
    # autoincrementing sequence column guarantees stable insertion-order
    # sorting regardless of timestamp collisions.
    seq = Column(Integer, Sequence("chat_messages_seq"), unique=True, nullable=True)