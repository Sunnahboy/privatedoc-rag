from abc import ABC, abstractmethod

from app.pipeline.retrieval.models import RetrievalChunk

from .models import GenerationResult


class BaseGenetrator(ABC):
    @abstractmethod
    async def generate(
        self,
        question: str,
        contact: list[RetrievalChunk],
    ) -> GenerationResult: ...
