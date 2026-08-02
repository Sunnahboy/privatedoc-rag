from typing import Annotated

from fastapi import APIRouter, Depends

from app.orchestration.rag_pipeline import RAGPipeline
from app.schemas.rag_schema import AskRequest, AskResponse, CitationResponse

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
):
    result = await pipeline.ask(request.question)

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
