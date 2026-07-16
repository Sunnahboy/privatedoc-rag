import re

from app.pipeline.extraction.models import ExtractionResult

from .base import BaseCleaner
from .models import CleaningResult


class TextCleaner(BaseCleaner):
    """
    Initial text cleaner.

    Current responsibilities:
    - Collapse multiple blank lines.

    Future:
    - Unicode normalization
    - Header/footer removal
    - Whitespace normalization
    """

    async def clean(self, extraction: ExtractionResult) -> CleaningResult:
        original = extraction.text

        cleaned = re.sub(r"\n\s*\n+", "\n\n", original)

        removed = original.count("\n\n") - cleaned.count("\n\n")

        return CleaningResult(
            text=cleaned,
            removed_blank_lines=max(removed, 0),
            metadata={},
        )
