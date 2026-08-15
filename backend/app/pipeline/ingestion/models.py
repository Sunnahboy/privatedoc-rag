from dataclasses import dataclass
from typing import Any

from app.pipeline.indexing.models import IndexingResult


@dataclass(slots=True)
class IngestionResult:
    indexing: IndexingResult
    total_chunks: int
    total_pages: int
    toc: list[dict[str, Any]] | None = None
