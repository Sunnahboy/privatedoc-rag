
from pathlib import Path
import aiofiles
from fastapi import UploadFile, HTTPException,status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import Document
from app.schemas.document_schema import (
    DocumentDeleteResponse,
    DocumentListItem,
    DocumentUploadResponse,
)
from app.utils.file_utils import(
    ensure_upload_dir,
    get_file_extension,
    sanitize_filename,
    validate_file_extension,
)
from app.utils.id_id_utils import generate_document_id
from app.config import settings

def _document_to_upload_response(document:Document) ->DocumentUploadResponse:
    return DocumentDeleteResponse(
        document_id=document.id,
        filename=document.stored_filename,
        original_filename=document.original_filename,
        file_extension=document.file_extension,
        file_size_bytes=document.file_size_bytes,
        storage_provider=document.storage_provider,
        storage_key=document.storage_key,
        status=document.status,
        total_pages=document.total_pages,
        total_chunks=document.total_chunks,
        created_at=document.created_at,

    )
def _document_to_list_item(document:Document) -> DocumentListItem:
    return DocumentListItem(
        document_id=document.id,
        original_filename=document.original_filename,
        file_extension=document.file_extension,
        file_size_bytes=document.file_size_bytes,
        storage_provider=document.storage_provider,
        storage_key=document.storage_key,
        status=document.status,
        total_pages=document.total_pages,
        total_chunks=document.total_chunks,
        created_at=document.created_at,
        updated_at=document.updated_at,

    )

async def save_uploaded_document(file:UploadFile,db:AsyncSession)-> DocumentUploadResponse:
    """
    Validate , save  and persist metadata for an uploaded document asynchronously.

    Why async:
    - Uploading files is I/O-bound.
    - The server waits for file data and disk writes.
    - Async lets the event loop handle other requests while this request waits.

    Why chunked reading:
    - Reading the entire file into memory is dangerous.
    - Large files can waste RAM or crash the process.
    - Chunked reading keeps memory usage predictable.
     also:
       -Raw files goes to local disk for now
       -metadata goes to sqlite.
       -Later, raw files can move to miniIO/s3
       -Later, metadata DB can move to postgresSql
    """


    if file.filename is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a filename.")
    
    original_filename = file.filename
    safe_filename = sanitize_filename(original_filename)
    validate_file_extension(safe_filename)
    document_id = generate_document_id()
    extension = get_file_extension(safe_filename)

    Upload_dir  = ensure_upload_dir()
    #store as doc_id + original safe extension
    stored_filename  = f"{document_id}{extension}"
    saved_path: Path  = Upload_dir / stored_filename
    
    total_size  = 0
    try:
        async with aiofiles.open(saved_path, "wb") as out_file:
            while True:
                chunk = await file.read(settings.CHUNK_SIZE_BYTES)
                if not chunk:
                    break
                total_size += len(chunk)

                if total_size > settings.max_upload_bytes:
                    await out_file.close()
                    saved_path.unlink(missing_ok=True)#clean  up partially written oversized files.
                    
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File too large. Maximum allowed size is {settings.max_upload_mb} MB.",
                    )
                
                await out_file.write(chunk)

            if total_size == 0:
                saved_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code= status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded file is empty"
                )
            

            document = Document(
                id=document_id,
                original_filename=original_filename,
                stored_filename=stored_filename,
                file_extension=extension,
                file_size_bytes=total_size,
                storage_provider="local",
                storage_key=stored_filename,
                status="uploaded",
                total_pages=0,
                total_chunks=0
            )

            db.add(document)
            await db.commit()
            await db.refresh(document)
            return _document_to_upload_response(document)
        
    except HTTPException:
        raise
    except Exception:
        #if db insert fails after file save, remove the saved file
        saved_path.unlink(missing_ok=True)
        await db.rollback()
        raise

    finally:
        await file.close()

    return DocumentUploadResponse(
        document_id=document_id,
        filename=stored_filename,
        original_filename= original_filename,
        file_extension=extension,
        file_size_bytes=total_size,
        status="uploaded",
        saved_path=str(saved_path)
    )
        
