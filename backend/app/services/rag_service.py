# app/services/rag_service.py

from pathlib import Path
from typing import Any

import fitz
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.pipeline.retrieval.multimodal_pipeline import MultimodalRetrievalPipeline
from app.utils.file_utils import ensure_upload_dir


class RAGService:
    """Legacy multimodal facade with the same tenant contract as ChatWorker."""

    def __init__(self, retrieval_pipeline: MultimodalRetrievalPipeline):
        self.pipeline = retrieval_pipeline

    async def answer_query(
        self,
        document_ids: list[str],
        user_id: str,
        query: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Retrieve and render context only from documents owned by ``user_id``."""
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")
        if not isinstance(document_ids, list) or not document_ids:
            raise ValueError("document_ids must be a non-empty list")
        if any(
            not isinstance(document_id, str) or not document_id
            for document_id in document_ids
        ):
            raise ValueError("document_ids must contain non-empty strings")

        # Deduplicate before querying and verify ownership before either
        # Qdrant retrieval or filesystem access. A guessed ID is not authority.
        scoped_document_ids = list(dict.fromkeys(document_ids))
        result = await db.execute(
            select(Document).where(
                Document.id.in_(scoped_document_ids),
                Document.user_id == user_id,
            )
        )
        owned_documents = result.scalars().all()
        documents_by_id = {document.id: document for document in owned_documents}
        if len(documents_by_id) != len(scoped_document_ids):
            # Do not identify which requested IDs belong to another tenant.
            raise PermissionError("One or more requested documents are unavailable.")

        # The lower retrieval layer independently applies its Qdrant/Tantivy
        # tenant filters. This database check prevents unauthorized IDs from
        # reaching it in the first place.
        retrieval_result = await self.pipeline.search(
            query=query,
            document_ids=scoped_document_ids,
            user_id=user_id,
        )

        rendered_images: list[Image.Image] = []
        mode_used = "text_only"

        if retrieval_result.has_strong_visual_match:
            mode_used = "multimodal"
            for visual_page in retrieval_result.visual_pages:
                origin_document_id = visual_page.get("document_id")
                document = documents_by_id.get(origin_document_id)
                page_number = visual_page.get("page_number")
                if document is None or not isinstance(page_number, int):
                    # Qdrant payload is defensive-in-depth checked against the
                    # SQL-owned document map before a path is ever constructed.
                    continue
                rendered_images.append(
                    self._render_page(document.storage_key, page_number)
                )

        return {
            "mode": mode_used,
            "cited_pages": [
                page for page, _score in retrieval_result.fused_page_ranks
            ],
            "text_chunks": retrieval_result.text_chunks,
            "images": rendered_images,
        }

    def _render_page(self, storage_key: str, page_number: int) -> Image.Image:
        """Render a page using an already-authorized database storage key."""
        upload_dir = ensure_upload_dir().resolve()
        file_path = (upload_dir / storage_key).resolve()
        if upload_dir not in file_path.parents:
            raise ValueError("Document storage key resolves outside the upload directory")
        if not file_path.is_file():
            raise FileNotFoundError("Authorized document file is missing")

        with fitz.open(file_path) as document:
            if not 0 < page_number <= len(document):
                raise ValueError("Requested page is outside the document")
            page = document[page_number - 1]
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            return Image.frombytes(
                "RGBA" if pix.alpha else "RGB",
                [pix.width, pix.height],
                pix.samples,
            )
