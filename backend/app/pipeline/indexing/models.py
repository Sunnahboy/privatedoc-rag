from dataclasses import dataclass

from app.pipeline.chunking.models import Chunk
from app.pipeline.embeddings.models import EmbeddingResult


@dataclass(slots=True)
class IndexingRequest:
    chunks: list[Chunk]
    embeddings: list[EmbeddingResult]
    # The ingestion worker supplies this from the authenticated job payload.
    # Both indexes stamp it onto every record before it becomes searchable.
    user_id: str


@dataclass(slots=True)
class IndexingResult:
    indexed_count: int
    collection_name: str
    user_id: str
