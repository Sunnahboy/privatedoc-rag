from abc import ABC, abstractmethod

from app.pipeline.cleaning.models import CleaningResult

from .models import Chunk


class BaseChunker(ABC):
    @abstractmethod
    async def chunk(
        self,
        cleaning_result: CleaningResult,
    ) -> list[Chunk]:
        """
        split cleaned text into searchable chunks.

        """
        ...
