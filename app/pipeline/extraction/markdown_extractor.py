from pathlib import Path

import anyio

from .base import BaseExtractor
from .models import ExtractionResult


class TXTExtractor(BaseExtractor):
    async def extract(self, file_path: Path) -> ExtractionResult:
        # open and read file async hence no blocking other
        async def read_file():
            await file_path.read_text(encoding="utf-8", errors="ignore")

        text = await anyio.to_thread.run_sync(read_file)

        return ExtractionResult(
            text=text,
            page_count=1,
            metadata={},
        )
