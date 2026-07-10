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

    async def extract(self, file_path: Path) -> ExtractionResult:
        document = None
        pages = []

        try:
            document = fitz.open(file_path)
            metadata = document.metadata
            for page in document:
                pages.append(page.get_text())
            return ExtractionResult(
                text="\n".join(pages),
                page_count=document.page_count,
                metadata=metadata,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to extract PDF {file_path}: {str(e)}")
        finally:
            if document is not None:
                document.close()
