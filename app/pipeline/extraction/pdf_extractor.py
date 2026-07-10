import asyncio
from pathlib import Path

import fitz  # PyMuPDF

from .base import BaseExtractor
from .models import ExtractionResult


class PDFExtractor(BaseExtractor):
    """
     Extract text from PDF documents.

    Why PyMuPDF?
    - Fast
    - Accurate
    - Returns page-by-page text
    - Gives access to metadata later

    """

    def _sync_extract(self, file_path: Path) -> ExtractionResult:
        # heavy lifting in a normal sync function
        try:
            with fitz.open(file_path) as document:
                pages = [page.get_text() for page in document]
                return ExtractionResult(
                    text="\n".join(pages),
                    page_count=document.page_count,
                    metadata=document.metadata,
                )
        except fitz.FileDataError as exc:
            raise RuntimeError(f"Invalid PDF: {file_path}") from exc

    async def extract(self, file_path: Path) -> ExtractionResult:
        # Run the heavy sync code in a separate thread
        return await asyncio.to_thread(self._sync_extract, file_path)
