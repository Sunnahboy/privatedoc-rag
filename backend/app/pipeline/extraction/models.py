from dataclasses import dataclass


@dataclass(slots=True)
class ExtractionResult:
    """
    Standard output from every extractor.

    Every document type (PDF, DOCX, PPTX, MD...)
    must return this object.

    This keeps the rest of the pipeline independent
    from file type.
    """

    text: str
    total_pages: int
    metadata: dict
