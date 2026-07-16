from dataclasses import dataclass


@dataclass(slots=True)
class CleaningResult:
    """
    Output of every cleaner.

    Why separate model?

    ExtractionResult represents raw extracted text.

    CleaningResult represents normalized text ready
    for chunking.
    Never overwrite raw extraction.
    """

    text: str
    removed_blank_lines: int
    metadata: dict
