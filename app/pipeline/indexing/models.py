from dataclasses import dataclass

from app.pipeline.chunking.models import Chunk
from app.pipeline.embeddings.models import EmbeddingResult


@dataclass(slots=True)
class IndexingRequest:
    chunks: list[Chunk]
    embeddings: list[EmbeddingResult]


@dataclass(slots=True)
class IndexingResult:
    indexed_count: int
    collection_name: str
