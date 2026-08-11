from dataclasses import dataclass

from app.pipeline.indexing.models import IndexingResult


@dataclass(slots=True)
class IngestionResult:
    indexing: IndexingResult
    total_chunks: int
    total_pages: int