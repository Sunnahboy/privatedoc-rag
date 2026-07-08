from fastapi import APIRouter , Depends, File, HTTPException,UploadFile,status
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from typing import Annotated
from app.database import get_db
from app.schemas.document_schema import(
    DocumentDeleteResponse,
    DocumentListItem,
    DocumentUploadResponse,
    
)
from app.services.document_service import(
    delete_document_by_id,
    list_documents,
    save_uploaded_document,
)

logger  = logging.getLogger(__name__)#tell which file generated the message

router  = APIRouter(prefix="/document", tags =["Documents"])

@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)


async def upload_document(file:Annotated[UploadFile, File(...)],db:Annotated[AsyncSession, Depends(get_db)])-> DocumentDeleteResponse:
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
        raise #silently swallow the error
    except Exception as exc:
        logger.exception("unexpected document upload failure %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error while uploading document.",
        )from exc
    
@router.get(
    "",
    response_model=list[DocumentListItem],
    status_code=status.HTTP_200_OK,
)

async def get_documents(db: Annotated[AsyncSession, Depends(get_db)])->list[DocumentListItem]:
    """
    List uploaded documents.

    why:
        -The frontend needs to show the available documents.
        -The user needs to know what has been uploaded.
        -Later, the user will choose which documents to chat with.

    """
    return await list_documents(db=db)

@router.delete(
    "/{document_id}",
    response_model=DocumentDeleteResponse,
    status_code=status.HTTP_200_OK,
    )
async def delete_document(document_id:str,db:Annotated[AsyncSession, Depends(get_db)])->DocumentDeleteResponse:
    """
    Delete an uploaded document.

    current behavior.
     -Delete local file.
     - Delete metadata row.

    Later behavior:
     -Delete chunks
     -Delete vectors from Qdrant.
     -Delete cached answers.
     -Delete graph records.
    
    """

    try:
        result = await delete_document_by_id(document_id=document_id, db=db)
        logger.info("Deleted document_id=%s",result.document_id)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected document delete failure: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error while deleting document."
        )from exc


