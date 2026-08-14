from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class CleaningResult:
    """
    Output of every cleaner.

    ExtractionResult represents raw extracted text.

    CleaningResult represents normalized text ready
    for chunking.
    """

    pages:list[str]
    removed_blank_lines: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
