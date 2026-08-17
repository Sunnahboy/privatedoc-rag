from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.document import Document
from app.utils.file_utils import ensure_upload_dir

router = APIRouter(prefix="/reader", tags=["Reader"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/{document_id}")
async def get_document_metadata(document_id: str, db: DbSession):
    """
    Fetches the document metadata for the frontend reader UI.
    This includes the filename, chunk counts, and the Table of Contents (TOC).
    """
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalars().first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/{document_id}/file")
async def get_document_file(document_id: str, db: DbSession):
    """
    Serves the raw PDF file bytes for the frontend PDFViewer.
    """
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalars().first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Reconstruct the file path using your upload directory
    upload_dir = ensure_upload_dir()
    file_path = upload_dir / doc.stored_filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File missing from disk")

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=doc.original_filename,
        # Required for frontend react-pdf to read 
        headers={"Access-Control-Expose-Headers": "Accept-Ranges, Content-Length"},
    )
