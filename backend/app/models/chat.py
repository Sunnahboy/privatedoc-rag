# app/models/chat.py
from sqlalchemy import Column, String, DateTime, JSON, Text, ForeignKey
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
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())