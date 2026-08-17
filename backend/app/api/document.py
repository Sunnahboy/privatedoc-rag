import logging
import mimetypes
import os
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
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
from app.utils.file_utils import ensure_upload_dir

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
    Upload a document and return its metadata.

    Validates and saves the file using async chunked I/O.
    The document is then queued for asynchronous ingestion,
    which handles extraction, cleaning, chunking, embedding, and indexing.
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
        raise
    except DuplicateDocumentError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A document with this exact content already exists. Existing ID: {e.existing_document_id}",
        )
    except Exception as exc:
        logger.exception(
            "unexpected document upload failure for filename: %s", file.filename,
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


@router.get(
    "/{document_id}/file",
    response_class=FileResponse,
    status_code=status.HTTP_200_OK,
)
async def get_document_file(
    document_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FileResponse:
    """
    Stream the raw document file directly to the client.
    Supports multiple formats (.pdf, .txt, .md, .ppt, .docx).
    """
    try:
        # Look up the document metadata
        doc = await get_document_by_id(document_id=document_id, db=db)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found.",
            )

        # Construct the exact file path using your existing utilities
        upload_dir = ensure_upload_dir()
        file_path = upload_dir / doc.storage_key

        # Check if physical file exists
        if not os.path.exists(file_path):
            logger.error(
                "Physical file missing for document_id=%s at path=%s",
                document_id,
                file_path,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Physical file missing from disk.",
            )

        # Guess the correct MIME type so the browser handles it correctly
        media_type, _ = mimetypes.guess_type(file_path)
        if not media_type:
            media_type = "application/octet-stream"  # Fallback for unknown binary types

        # Stream the file
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=doc.original_filename,
            content_disposition_type="inline",
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "Unexpected error fetching file for document_id: %s", document_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error while retrieving the document file.",
        ) from exc
