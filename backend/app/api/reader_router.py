from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.document import Document

router = APIRouter(prefix="/reader", tags=["Reader"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/{document_id}")
async def get_document_metadata(document_id: str, db: DbSession):
    """
    Fetches the document metadata for the Next.js reader UI.
    This includes the filename, chunk counts, and the Table of Contents (TOC).
    """
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalars().first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
