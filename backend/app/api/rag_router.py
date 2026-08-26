from typing import Annotated, AsyncGenerator,List
from app.pipeline.retrieval.multimodal_retriever import MultimodalRetriever
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.pipeline.retrieval.bm25_retriever import BM25Retriever
from app.pipeline.retrieval.hybrid_retriever import HybridRetriever
from app.database import get_db
from app.orchestration.rag_pipeline import RAGPipeline
from app.schemas.rag_schema import AskRequest, AskResponse, CitationResponse
from app.services import document_service
from app.pipeline.retrieval.multimodal_pipeline import MultimodalRetrievalPipeline
from app.schemas.rag_schema import AskRequest, AskResponse, CitationResponse
from app.services import document_service
from app.pipeline.retrieval.qdrant_retriever import QdrantRetriever
from app.pipeline.embeddings.visual_engine import VisualRetrieverEngine
from app.pipeline.embeddings.ollama_embedder import OllamaEmbedder
from qdrant_client import AsyncQdrantClient
from app.config import settings
import uuid
from sqlalchemy import select, desc
from app.models.chat import ChatSession, ChatMessage
import json
from fastapi import Request
from fastapi.responses import StreamingResponse
router = APIRouter(
    prefix="/rag",
    tags=["RAG"],
)


async def get_pipeline() -> AsyncGenerator[RAGPipeline, None]:
    """Instatiate the pipeline with multimodel capabilities and ensures cleaneup."""
    base_retriever = HybridRetriever(
        dense=QdrantRetriever(),
        sparse=BM25Retriever(),
    )
    qdrant_client = AsyncQdrantClient(url=settings.qdrant_url) 
    visual_engine = VisualRetrieverEngine()
    #Instantiate the actual Multimodal Retriever
    multi_retriever = MultimodalRetriever(
        qdrant_client=qdrant_client,
        text_retriever=base_retriever,
        visual_engine=visual_engine
    )

    # Pass base_retriever into MultimodalRetrievalPipeline
    multimodal = MultimodalRetrievalPipeline(retriever=multi_retriever)

    #Instantiate RAGPipeline with both
    pipeline = RAGPipeline(
        retriever=base_retriever,
        multimodal_pipeline=multimodal,
    )
    try:
        yield pipeline
    finally:
        await pipeline.close()

async def get_or_create_session(session_id: str | None, db: AsyncSession, title_fallback: str) -> str:
    """Finds existing session or creates a new one."""
    if session_id:
        result = await db.execute(select(ChatSession).filter(ChatSession.id == session_id))
        session = result.scalars().first()
        if session:
            return session.id

    new_id = str(uuid.uuid4())
    new_session = ChatSession(id=new_id, title=title_fallback[:60])
    db.add(new_session)
    await db.commit()
    return new_id

async def fetch_sliding_window_history(session_id: str, db: AsyncSession, limit: int = 4) -> List[ChatMessage]:
    """Fetches the last N messages to prevent LLM context overflow."""
    stmt = (
        select(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(desc(ChatMessage.created_at))
        .limit(limit)
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()
    return list(reversed(messages))


@router.post("/ask")
async def ask(
    request: Request,           
    payload: AskRequest,
    pipeline: Annotated[RAGPipeline, Depends(get_pipeline)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """The API doorway to  RAG pipeline it validates the request,
    uses Server-Sent Events (SSE) to stream tokens in real-time."""

    if payload.document_id:
        document = await document_service.get_document_by_id(
            payload.document_id,
            db,
        )

        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{payload.document_id}' not found.",
            )
            # Resolve the Chat Session
    active_session_id = await get_or_create_session(
        session_id=payload.session_id,
        db=db,
        title_fallback=payload.question
    )

    # Grab the Sliding Window History
    recent_history = await fetch_sliding_window_history(active_session_id, db)

    # Save the User's Question instantly
    user_msg = ChatMessage(
        id=str(uuid.uuid4()),
        session_id=active_session_id,
        role="user",
        content=payload.question,
        citations=[]
    )
    db.add(user_msg)
    await db.commit()


    #Define the Async Generator for SSE
    async def event_generator():
        # Send the session_id immediately so the frontend knows it
        yield f"data: {json.dumps({'type': 'session', 'session_id': active_session_id})}\n\n"

        full_text = ""
        final_citations = []

        try:
            async for chunk in pipeline.ask_stream(
                question=payload.question,
                document_id=payload.document_id,
                chat_history=recent_history,
            ):
                # Detect if the frontend hit "Stop" or the user closed the tab
                if await request.is_disconnected():
                    print("Client disconnected! Aborting stream.")
                    break

                # Send the chunk to the frontend
                yield f"data: {json.dumps(chunk)}\n\n"

                # Keep track of text and citations so  can save to DB
                chunk_type = chunk.get("type")
                if chunk_type == "token":
                    full_text += chunk.get("content", "")
                elif chunk_type == "done":
                    final_citations = chunk.get("citations", [])
                    
        except Exception as e:
            # Send error cleanly down the stream
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
            return
            
        # Save the completed Assistant message to PostgreSQL
        formatted_citations = [
            {
                "document_id": c.get("document_id", payload.document_id),
                "chunk_index": c.get("chunk_index"),
                "text": c.get("text"),
                "score": float(c.get("score", 0.0))
            } for c in final_citations
        ]

        assistant_msg = ChatMessage(
            id=str(uuid.uuid4()),
            session_id=active_session_id,
            role="assistant",
            content=full_text,
            citations=formatted_citations
        )
        db.add(assistant_msg)
        await db.commit()

    # 5. Return the Streaming Response using the SSE media type
    return StreamingResponse(event_generator(), media_type="text/event-stream")

    
