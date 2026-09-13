from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models.document import Document
from app.utils.file_utils import ensure_upload_dir

router = APIRouter(prefix="/reader", tags=["Reader"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[str, Depends(get_current_user)]


@router.get("/{document_id}")
async def get_document_metadata(
    document_id: str, db: DbSession, current_user_id: CurrentUser
):
    """
    Fetches the document metadata for the frontend reader UI.
    This includes the filename, chunk counts, and the Table of Contents (TOC).
    """
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user_id,
        )
    )
    doc = result.scalars().first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    return doc


@router.get("/{document_id}/file")
async def get_document_file(
    document_id: str, db: DbSession, current_user_id: CurrentUser
):
    """
    Serves the raw PDF file bytes for the frontend PDFViewer.
    Enforces tenant isolation.
    """
    result = await db.execute(
        select(Document).where(
            Document.id == document_id, Document.user_id == current_user_id
        )
    )
    doc = result.scalars().first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    # Reconstruct the file path using your upload directory
    upload_dir = ensure_upload_dir()
    file_path = upload_dir / doc.stored_filename

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File missing from disk"
        )

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=doc.original_filename,
        # Required for frontend react-pdf to read
        headers={"Access-Control-Expose-Headers": "Accept-Ranges, Content-Length"},
    )
