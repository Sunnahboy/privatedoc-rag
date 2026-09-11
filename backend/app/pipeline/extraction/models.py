from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ExtractionResult:
    """
    Standard output from every extractor.

    Every document type (PDF, DOCX, PPTX, MD...)
    must return this object.

    This keeps the rest of the pipeline independent
    from file type.
    """

    pages: list[str]
    total_pages: int
    toc: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    # The real page number backing each entry in `pages` (e.g. Docling's own
    # page keys). Extractors can skip pages, so `pages[i]` is not always
    # page `i + 1` - callers must use this instead of the array index.
    page_numbers: list[int] = field(default_factory=list)
