from abc import ABC, abstractmethod

from app.pipeline.retrieval.models import RetrievedChunk

from .models import GenerateResult


class BaseGenerator(ABC):
    @abstractmethod
    async def generate(
        self,
        question: str,
        contact: list[RetrievedChunk],
    ) -> GenerateResult: ...
