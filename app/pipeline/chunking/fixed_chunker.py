import uuid

from app.pipeline.cleaning.models import CleaningResult

from .base import BaseChunker
from .models import Chunk


class fixedChunker(BaseChunker):
    def __init__(self, chunk_size: int = 500):
        if chunk_size < 0:
            raise ValueError("chunk size must be greater than zero")
        self.chunk_size = chunk_size

    async def chunk(
        self,
        cleaning_result: CleaningResult,
    ) -> list[Chunk]:
        text = cleaning_result.text
        chunks: list[Chunk] = []

        for start in range(0, len(text), self.chunk_size):
            end = min(start + self.chunk, len(text))

            chunks.append(
                Chunk(
                    Chunk_id=str(uuid),
                    text=text[start:end],
                    start_char=start,
                    end_char=end,
                )
            )
        return chunks
