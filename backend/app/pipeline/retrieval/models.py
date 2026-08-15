from dataclasses import dataclass


@dataclass(slots=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    chunk_index: int
    text: str
    score: float
    page_number: int | None = None


@dataclass(slots=True)
class RetrievalResult:
    chunks: list[RetrievedChunk]
    found: bool
    message: str | None = None
    dense_hits: int = 0
    sparse_hits: int = 0
    fused_hits: int = 0
