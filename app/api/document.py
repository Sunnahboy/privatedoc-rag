from fastapi import APIRouter , File, HTTPException,UploadFile,status
import logging
from app.schemas.document_schema import DocumentUploadResponse
from app.services.document_service import save_uploaded_document

logger  = logging.getLogger(__name__)#tell which file generated the message

router  = APIRouter(prefix="/document", tags =["Documents"])

@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)


async def upload_document(file:UploadFile = File(...))-> DocumentUploadResponse:
    """
    Upload a document.

    What this endpoint does now:
    - Receives file upload.
    - Validates filename, extension, and size.
    - Saves file safely using async chunked file I/O.
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
    """

    try:
        result = await save_uploaded_document(file)

        logger.info(
            "Uploaded document_id=%s filename=%s size=%s bytes",
            result.document_id,
            result.filename,
            result.file_size_bytes,
        )
        return result
    except HTTPException:
        raise #silently swallow the error
    except Exception as exc:
        logger.exception("unexpected document upload failure %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error while uploading document.",
        )from exc



