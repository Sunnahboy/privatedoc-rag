import uuid

from app.config import settings
from app.pipeline.cleaning.models import CleaningResult

from .base import BaseChunker
from .models import Chunk


class FixedChunker(BaseChunker):
    def __init__(self, chunk_size: int | None = None, overlap: int | None = None):
        self.chunk_size = chunk_size or settings.rag_chunk_size
        self.overlap = overlap or settings.rag_chunk_overlap

        if self.chunk_size <= 0:
            raise ValueError("chunk size must be greater than zero")
        self.chunk_size = chunk_size

        if self.overlap < 0:
            raise ValueError("Overlap cannot be negative")
        if self.overlap >= self.chunk_size:
            raise ValueError("Overlap cannot be smaller than chunk_size")

    async def chunk(
        self,
        cleaning_result: CleaningResult,
    ) -> list[Chunk]:
        text = cleaning_result.text
        chunks: list[Chunk] = []
        stride = self.chunk_size - self.overlap

        for start in range(0, len(text), stride):
            end = min(start + self.chunk_size, len(text))

            chunks.append(
                Chunk(
                    chunk_id=str(uuid.uuid4()),
                    text=text[start:end],
                    start_char=start,
                    end_char=end,
                )
            )
        return chunks
