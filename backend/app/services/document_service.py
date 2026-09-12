import logging
from pathlib import Path

import aiofiles
import fitz
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.messaging.publisher import publish_ingestion_job
from app.models.document import Document, IngestStatus
from app.pipeline.indexing.composite_indexer import CompositeIndexer
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

logger = logging.getLogger(__name__)


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

        # SANITIZE PDF ANNOTATIONS

        try:
            doc = fitz.open(saved_path)
            annotations_removed = 0
            for page in doc:
                annot = page.first_annot
                while annot:
                    next_annot = annot.next
                    # Types 8, 9, 10, 11 are Highlight, Underline, Squiggly, StrikeOut
                    if annot.type[0] in [8, 9, 10, 11]:
                        page.delete_annot(annot)
                        annotations_removed += 1
                    annot = next_annot

            if annotations_removed > 0:
                doc.save(saved_path, incremental=False, garbage=3, deflate=True)
            doc.close()
        except Exception as e:#noqa
            # If it's not a PDF or PyMuPDF fails, skip gracefully
            logger.warning(f"Could not sanitize annotations for {saved_path.name}: {e}")

        return total_size

    except Exception:
        # Clean up partially written files if anything goes wrong during I/O
        saved_path.unlink(missing_ok=True)
        raise


async def save_uploaded_document(
    file: UploadFile, db: AsyncSession,user_id:str,
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
        # SECURITY: Deduplication must be scoped to the user. 
        # User A uploading 'tax.pdf' shouldn't block User B from uploading identical 'tax.pdf'.
        existing_query = await db.execute(
            select(Document).where(
                Document.content_hash == content_hash),
                Document.user_id == user_id,#tenant loc
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
            user_id=user_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_extension=extension,
            file_size_bytes=total_size,
            content_hash=content_hash,
            storage_provider="local",
            storage_key=stored_filename,
            status=IngestStatus.QUEUED,
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
            # Re-check the tenant-scoped query in case of a race condition
            race_query = await db.execute(
                select(Document).where(
                    Document.content_hash == content_hash,
                    Document.user_id == user_id,
                )
            )
            race_winner = race_query.scalars().first()
            if race_winner:
                return _document_to_upload_response(race_winner)
            raise  # Re-raise if the error wasn't due to the uniqueness constraint

        await db.refresh(document)

        # Route to heavy ingestion pipeline
        await publish_ingestion_job(
            document_id=document.id, 
            storage_key=document.storage_key,
            user_id =user_id,
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


async def get_document_by_id(
    document_id: str, db: AsyncSession, user_id:str
) -> DocumentListItem | None:
    """
    Fetch a single document by its ID and return a DocumentListItem schema.
    Used by the frontend polling mechanism to check upload status.
    
    """
    #SECURITY: Ensure the user owns the document they are polling
    stmt = select(Document).where(
        Document.id == document_id,
        Document.user_id == user_id,
        )

    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    # Convert ORM model to Pydantic response model to satisfy FastAPI response validation
    return _document_to_list_item(doc) if doc else None


async def validate_document_ids(requested_ids: list[str], db: AsyncSession, user_id:str) -> set[str]:
    """
    Fetches valid IDs in O(1) network calls.
    Returns the set of IDs that were NOT found in the database.
    """
    if not requested_ids:
        return set()

    stmt = select(Document.id).filter(
        Document.id.in_(requested_ids),
        Document.user_id ==user_id,
        )
    result = await db.execute(stmt)
    found_ids = set(result.scalars().all())

    return set(requested_ids) - found_ids


async def list_documents(db: AsyncSession, user_id:str) -> list[DocumentListItem]:
    """
    Return all uploaded documents.

    why ordered newest to first:
     - Users usually care about recently uploaded documents first.
    """
    result = await db.execute(
        select(Document)
        .where(Document.user_id == user_id)
        .order_by(Document.created_at.desc()))

    Documents = result.scalars().all()
    return [_document_to_list_item(document) for document in Documents]


async def delete_document_by_id(
    document_id: str, db: AsyncSession,user_id:str
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

    stmt = select(Document).where(
        Document.id == document_id,
        Document.user_id == user_id
    )
    result  = await db.execute(stmt)
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )
    indexer = CompositeIndexer()
    try:
        #NBmust update CompositeIndexer to accept user_id so it deletes from the user's isolated Qdrant/Tantivy space
        await indexer.delete_document(document_id, user_id=user_id)
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
