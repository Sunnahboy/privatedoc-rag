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


@router.post("/ask", response_model=AskResponse)
async def ask(
    request: AskRequest,
    pipeline: Annotated[RAGPipeline, Depends(get_pipeline)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """The API doorway to  RAG pipeline it validates the request,
    calls the pipeline, and formats the result for the frontend."""

    if request.document_id:
        document = await document_service.get_document_by_id(
            request.document_id,
            db,
        )

        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{request.document_id}' not found.",
            )
            # Resolve the Chat Session
    active_session_id = await get_or_create_session(
        session_id=request.session_id,
        db=db,
        title_fallback=request.question
    )

    # Grab the Sliding Window History
    recent_history = await fetch_sliding_window_history(active_session_id, db)

    # Save the User's Question instantly
    user_msg = ChatMessage(
        id=str(uuid.uuid4()),
        session_id=active_session_id,
        role="user",
        content=request.question,
        citations=[]
    )
    db.add(user_msg)
    await db.commit()

    result = await pipeline.ask(
        question=request.question,
        document_id=request.document_id,
        chat_history=recent_history,
    )

    # Format the citations so they can be saved as JSON in PostgreSQL
    formatted_citations = [
        {
            "document_id": c.document_id,
            "chunk_index": c.chunk_index,
            "text": c.text,
            "score": float(c.score)
        } for c in result.citations
    ]

    #Save the Assistant's Answer
    assistant_msg = ChatMessage(
        id=str(uuid.uuid4()),
        session_id=active_session_id,
        role="assistant",
        content=result.answer,
        citations=formatted_citations
    )
    db.add(assistant_msg)
    await db.commit()

    return AskResponse(
        session_id=active_session_id,
        answer=result.answer,
        citations=[
            CitationResponse(
                document_id=c.document_id,
                chunk_index=c.chunk_index,
                text=c.text,
                score=c.score,
            )
            for c in result.citations
        ],
    )
