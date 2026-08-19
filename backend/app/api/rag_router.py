from typing import Annotated, AsyncGenerator
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
    text_embedder = OllamaEmbedder() 
    visual_engine = VisualRetrieverEngine()
    #Instantiate the actual Multimodal Retriever
    multi_retriever = MultimodalRetriever(
        qdrant_client=qdrant_client,
        text_embedder=text_embedder,
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
    result = await pipeline.ask(
        question=request.question,
        document_id=request.document_id,
    )

    return AskResponse(
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
