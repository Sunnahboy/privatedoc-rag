import re

from app.pipeline.extraction.models import ExtractionResult

from .base import BaseCleaner
from .models import CleaningResult


class TextCleaner(BaseCleaner):
    """
    Initial text cleaner, operating page-by-page.

    Current responsibilities:
    - Normalize line endings.
    - Remove common PDF extraction artifacts.
    - Trim trailing whitespace.
    - Collapse multiple blank lines.
    """

    async def _clean_single_page(self, text: str) -> tuple[str, int, int, int]:
        original = text or ""

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
        return cleaned, removed, len(original), len(cleaned)

    async def clean(self, extraction: ExtractionResult) -> CleaningResult:
        cleaned_pages = []
        total_removed_lines = 0
        total_original_length = 0
        total_cleaned_length = 0

        # Safely handle the new pages list, or fallback if older pipeline data is passed
        pages = getattr(extraction, "pages", [])
        if not pages and getattr(extraction, "text", None):
            pages = [extraction.text]

        for page_text in pages:
            cleaned, removed, orig_len, clean_len = self._clean_single_page(page_text)
            cleaned_pages.append(cleaned)
            total_removed_lines += removed
            total_original_length += orig_len
            total_cleaned_length += clean_len

        return CleaningResult(
            pages=cleaned_pages,
            removed_blank_lines=total_removed_lines,
            metadata={
                "original_length": total_original_length,
                "cleaned_length": total_cleaned_length,
            },
        )
