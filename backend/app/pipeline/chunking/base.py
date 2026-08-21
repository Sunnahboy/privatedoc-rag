from abc import ABC, abstractmethod

from app.pipeline.cleaning.models import CleaningResult

from .models import Chunk


class BaseChunker(ABC):
    @abstractmethod
    async def chunk(
        self,
        cleaning_result: CleaningResult,
        document_id: str = "unknown_doc",
    ) -> list[Chunk]:
        """
        split cleaned text into searchable chunks.

        """
        ...
