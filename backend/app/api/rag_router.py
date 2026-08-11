from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.orchestration.rag_pipeline import RAGPipeline
from app.schemas.rag_schema import AskRequest, AskResponse, CitationResponse
from app.services import document_service

router = APIRouter(
    prefix="/rag",
    tags=["RAG"],
)


async def get_pipeline() -> RAGPipeline:
    return RAGPipeline()


@router.post("/ask", response_model=AskResponse)
async def ask(
    request: AskRequest,
    pipeline: Annotated[get_pipeline, Depends(get_pipeline)],
    db: Annotated[AsyncSession, Depends(get_db)],
):

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
