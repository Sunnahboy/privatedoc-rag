# app/services/rag_service.py

from pathlib import Path
from typing import Any

import fitz
from app.config import settings
from app.pipeline.retrieval.multimodal_pipeline import MultimodalRetrievalPipeline
from PIL import Image


class RAGService:
    def __init__(self, retrieval_pipeline: MultimodalRetrievalPipeline):
        self.pipeline = retrieval_pipeline

    async def answer_query(self, document_id: str, query: str) -> dict[str, Any]:
        # Step 1: Retrieve context
        result = await self.pipeline.search(query=query, document_id=document_id)

        rendered_images: list[Image.Image] = []
        mode_used = "text_only"

        # Step 2: Adaptive Context Assembly
        if result.has_strong_visual_match:
            mode_used = "multimodal"
            # Render all matched visual pages (or just the top one)
            for vp in result.visual_pages:
                page_num = vp["page_number"]
                img = self._render_page(document_id, page_num)
                rendered_images.append(img)

        return {
            "mode": mode_used,
            "cited_pages": [p[0] for p in result.fused_page_ranks],
            "text_chunks": result.text_chunks,
            "images": rendered_images,  # <--- Now 'image'/'rendered_images' is accessed and returned!
        }

    def _render_page(self, document_id: str, page_number: int) -> Image.Image:
        pdf_path = Path(settings.UPLOAD_DIR) / f"{document_id}.pdf"
        doc = fitz.open(pdf_path)
        page = doc[page_number - 1]
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
        img = Image.frombytes(
            "RGBA" if pix.alpha else "RGB", [pix.width, pix.height], pix.samples
        )
        doc.close()
        return img
