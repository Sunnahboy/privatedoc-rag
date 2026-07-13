from pathlib import Path

import anyio
from docx import Document

from .base import BaseExtractor, ExtractionResult


class DOCXExtractor(BaseExtractor):
    """
    Extract text from word
    """

    def _syc_extract(self, file_path: Path) -> ExtractionResult:
        document = Document(file_path)

        paragraphs = [
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        ]

        return ExtractionResult(
            text="\n".join(paragraphs),
            page_count=1,
            metadata={"paragraphs": len(paragraphs)},
        )

    async def extract(self, file_path: Path) -> ExtractionResult:
        return await anyio.to_thread.run_sync(
            self._syc_extract,
            file_path,
        )
