from pathlib import Path

import aiofiles
from app.config import settings
from app.models.document import Document
from app.pipeline.indexing.composite_indexer import CompositeIndexer
from app.pipeline.ingestion.pipeline import IngestionPipeline
from app.schemas.document_schema import (
    DocumentDeleteResponse,
    DocumentListItem,
    DocumentUploadResponse,
)
from app.utils.file_utils import (
    ensure_upload_dir,
    get_file_extension,
    sanitize_filename,
    validate_file_extension,
)
from app.utils.hashing import calculate_upload_stream_hash
from app.utils.id_id_utils import generate_document_id
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class DuplicateDocumentError(Exception):
    """Raised when an uploaded document's SHA-256 hash already exists in the database."""

    def __init__(self, existing_document_id: str):
        self.existing_document_id = existing_document_id
        super().__init__(f"Duplicate document. ID: {existing_document_id}")


def _document_to_upload_response(document: Document) -> DocumentUploadResponse:
    return DocumentUploadResponse(
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


def _document_to_list_item(document: Document) -> DocumentListItem:
    return DocumentListItem(
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
        updated_at=document.updated_at,
    )


async def _save_file_to_disk(file: UploadFile, saved_path: Path) -> int:
    """
    Safely reads an UploadFile in chunks and writes it to disk.
    Enforces maximum size limits and cleans up upon failure.

    Returns:
        int: The total size of the file in bytes.
    """
    total_size = 0

    try:
        async with aiofiles.open(saved_path, "wb") as out_file:
            while True:
                chunk = await file.read(settings.file_stream_chunk_size_bytes)
                if not chunk:
                    break

                total_size += len(chunk)

                if total_size > settings.max_upload_bytes:
                    await out_file.close()
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File too large. Maximum allowed size is {settings.max_upload_mb} MB.",
                    )

                await out_file.write(chunk)

        if total_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty",
            )

        return total_size

    except Exception:
        # Clean up partially written files if anything goes wrong during I/O
        saved_path.unlink(missing_ok=True)
        raise


from sqlalchemy.exc import IntegrityError


async def save_uploaded_document(
    file: UploadFile, db: AsyncSession
) -> DocumentUploadResponse:
    """
    Validate, save and persist metadata for an uploaded document asynchronously.
    """
    try:
        if file.filename is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file must have a filename.",
            )

        original_filename = file.filename
        safe_filename = sanitize_filename(original_filename)
        validate_file_extension(safe_filename)
        extension = get_file_extension(safe_filename)

        # 1. Hash the incoming stream & check DB for duplicates
        content_hash = await calculate_upload_stream_hash(file)

        existing_query = await db.execute(
            select(Document).where(Document.content_hash == content_hash)
        )
        existing_doc = existing_query.scalars().first()

        if existing_doc:
            # Raise the custom exception for the API router to catch and return 409
            raise DuplicateDocumentError(existing_document_id=existing_doc.id)

        # 2. Setup storage paths
        document_id = generate_document_id()
        upload_dir = ensure_upload_dir()
        stored_filename = f"{document_id}{extension}"
        saved_path: Path = upload_dir / stored_filename

        # 3. Offload disk I/O to the helper function
        total_size = await _save_file_to_disk(file, saved_path)

        # 4. Save to Database
        document = Document(
            id=document_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_extension=extension,
            file_size_bytes=total_size,
            content_hash=content_hash,
            storage_provider="local",
            storage_key=stored_filename,
            status="processing",
            total_pages=0,
            total_chunks=0,
        )

        db.add(document)

        try:
            await db.commit()
        except IntegrityError:
            # Race condition fallback: two users uploaded the same file simultaneously
            await db.rollback()
            saved_path.unlink(missing_ok=True)

            race_query = await db.execute(
                select(Document).where(Document.content_hash == content_hash)
            )
            race_winner = race_query.scalars().first()
            if race_winner:
                return _document_to_upload_response(race_winner)
            raise  # Re-raise if the error wasn't due to the uniqueness constraint

        await db.refresh(document)

        # 5. Route to heavy ingestion pipeline
        await _process_document(
            document=document,
            saved_path=saved_path,
            db=db,
        )

        return _document_to_upload_response(document)

    except HTTPException:
        raise
    except DuplicateDocumentError:
        raise
    except Exception:
        # If DB insert fails after file save, remove the saved file
        if "saved_path" in locals():
            saved_path.unlink(missing_ok=True)
        await db.rollback()
        raise
    finally:
        await file.close()


async def _process_document(
    document: Document,
    saved_path: Path,
    db: AsyncSession,
) -> None:
    """Execute the ingestion pipeline and update document status."""
    pipeline = IngestionPipeline()

    try:
        result = await pipeline.ingest(
            document_id=document.id,
            file_path=saved_path,
        )
        document.status = "indexed"
        document.total_chunks = result.total_chunks
        document.total_pages = result.total_pages
    except Exception:
        await db.rollback()
        document.status = "failed"
        await db.commit()
        await db.refresh(document)
        raise
    else:
        await db.commit()
        await db.refresh(document)
    finally:
        await pipeline.close()


async def list_documents(db: AsyncSession) -> list[DocumentListItem]:
    """
    Return all uploaded documents.

    why ordered newest to first:
     - Users usually care about recently uploaded documents first.
    """
    result = await db.execute(select(Document).order_by(Document.created_at.desc()))

    Documents = result.scalars().all()
    return [_document_to_list_item(document) for document in Documents]


async def delete_document_by_id(
    document_id: str, db: AsyncSession
) -> DocumentDeleteResponse:
    """
    Delete one document.

    Current deletion behavior:
     - Delete vectors from Qdrant.
     - Delete BM25 entries from Tantivy.
     - Delete local file.
     - Delete metadata row.

    Future deletion behavior:
     - Delete cached answers.
     - Delete graph entities and relationships.
    """

    document = await db.get(Document, document_id)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )
    indexer = CompositeIndexer()
    try:
        await indexer.delete_document(document_id)
        upload_dir = ensure_upload_dir()
        saved_path = upload_dir / document.storage_key
        saved_path.unlink(missing_ok=True)

        await db.delete(document)
        await db.commit()
    finally:
        await indexer.close()

    return DocumentDeleteResponse(
        document_id=document_id,
        deleted=True,
    )
