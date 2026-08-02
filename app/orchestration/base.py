from abc import ABC, abstractmethod

from app.pipeline.generation.models import GenerateResult


class BaseRAGPipeline(ABC):
    @abstractmethod
    async def ask(
        self,
        question: str,
    ) -> GenerateResult: ...
