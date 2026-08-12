import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.document_schema import (
    DocumentDeleteResponse,
    DocumentListItem,
    DocumentUploadResponse,
)
from app.services.document_service import (
    DuplicateDocumentError,
    delete_document_by_id,
    get_document_by_id,
    list_documents,
    save_uploaded_document,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/document", tags=["Documents"])


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    file: Annotated[UploadFile, File(...)], db: Annotated[AsyncSession, Depends(get_db)]
) -> DocumentUploadResponse:
    """
    Upload a document.

    What this endpoint does now:
    - Receives file upload.
    - Validates filename, extension, and size.
    - Saves(sqlite) file safely using async chunked file I/O.
    - Returns document metadata.

    What this endpoint does NOT do yet:
    - PDF extraction.
    - Chunking.
    - Embedding.
    - Qdrant storage.
    - RAG answering.

    Why:
    - Uploading is I/O bound.
    - Async upload handling improves concurrency.
     -Chunked saving avoids loading large files into memory.

     Later behavior:
     -Trigger indexing.
     -Extract text.
     -Chunk content.
     -Generate embeddings.
     -Store vectors in Qdrant.
    """

    try:
        result = await save_uploaded_document(file=file, db=db)

        logger.info(
            "Uploaded document_id=%s filename=%s size=%s bytes",
            result.document_id,
            result.filename,
            result.file_size_bytes,
        )

        return result
    except HTTPException:
        raise  # silently swallow the error
    except DuplicateDocumentError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A document with this exact content already exists. Existing ID: {e.existing_document_id}",
        )
    except Exception as exc:
        logger.exception(
            "unexpected document upload failure for filename: %s",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error while uploading document.",
        ) from exc


@router.get(
    "",
    response_model=list[DocumentListItem],
    status_code=status.HTTP_200_OK,
)
async def list_documents_endpoint(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DocumentListItem]:
    """
    Return all uploaded documents. Defined before the detail route so FastAPI
    doesn't treat the empty path as a document_id.
    """
    try:
        return await list_documents(db=db)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "Unexpected error listing documents: %s",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error while listing documents.",
        ) from exc


@router.get(
    "/{document_id}",
    response_model=DocumentListItem,
    status_code=status.HTTP_200_OK,
)
async def get_document(
    document_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentListItem:
    """
    Fetch a single document by ID. The service returns a DocumentListItem
    schema (or None) so this router simply forwards that result or raises 404.
    """
    try:
        doc = await get_document_by_id(document_id=document_id, db=db)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found.",
            )
        return doc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "Unexpected error fetching document_id: %s",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error while fetching document.",
        ) from exc


@router.delete(
    "/{document_id}",
    response_model=DocumentDeleteResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_document(
    document_id: str, db: Annotated[AsyncSession, Depends(get_db)]
) -> DocumentDeleteResponse:
    """
    Delete an uploaded document.

    Current behavior:
     - Delete vectors from Qdrant.
     - Delete BM25 entries from Tantivy.
     - Delete local file.
     - Delete metadata row.

    Future behavior:
     - Delete cached answers.
     - Delete graph records.
    """

    try:
        result = await delete_document_by_id(document_id=document_id, db=db)
        logger.info("Deleted document_id=%s", result.document_id)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected document delete failure for document_id: %s")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error while deleting document.",
        ) from exc
