from dataclasses import dataclass


@dataclass(slots=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    chunk_index: int
    text: str
    score: float


@dataclass(slot=True)
class RetrievalResult:
    chunks: list[RetrievedChunk]
