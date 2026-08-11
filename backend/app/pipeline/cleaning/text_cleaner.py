import re

from app.pipeline.extraction.models import ExtractionResult

from .base import BaseCleaner
from .models import CleaningResult


class TextCleaner(BaseCleaner):
    """
    Initial text cleaner.

    Current responsibilities:
    - Normalize line endings.
    - Remove common PDF extraction artifacts.
    - Trim trailing whitespace.
    - Collapse multiple blank lines.

    Future:
    - Unicode normalization
    - Header/footer removal
    - Page number removal
    - OCR cleanup
    """

    async def clean(self, extraction: ExtractionResult) -> CleaningResult:
        original = extraction.text or ""

        # Normalize line endings
        cleaned = original.replace("\r\n", "\n").replace("\r", "\n")
        # Remove common PDF extraction artifacts
        cleaned = (
            cleaned.replace("\ufeff", "")  # BOM
            .replace("\u200b", "")  # Zero-width space
            .replace("\u200c", "")  # Zero-width non-joiner
            .replace("\u200d", "")  # Zero-width joiner
            .replace("\xad", "")  # Soft hyphen
            .replace("\x00", "")  # Null character
        )
        # Remove trailing spaces/tabs from each line
        cleaned = re.sub(
            r"[ \t]+$",
            "",
            cleaned,
            flags=re.MULTILINE,
        )
        # Collapse multiple blank lines
        cleaned = re.sub(
            r"\n{3,}",
            "\n\n",
            cleaned,
        )

        removed = max(
            original.count("\n\n") - cleaned.count("\n\n"),
            0,
        )

        return CleaningResult(
            text=cleaned,
            removed_blank_lines=max(removed, 0),
            metadata={
                "original_length": len(original),
                "cleaned_length": len(cleaned),
            },
        )
