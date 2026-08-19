from abc import ABC, abstractmethod
from PIL import Image
from app.pipeline.retrieval.models import RetrievedChunk
from typing import Any
from .models import GenerateResult


class BaseGenerator(ABC):
    @abstractmethod
    async def generate(
        self,
        question: str,
        context: list[RetrievedChunk],
        images: list[Image.Image] | None = None,
    ) -> GenerateResult:
        """
        Generates an answer based on the provided question and context.
        Optionally accepts a list of PIL Images for multimodal generation.
        """
           
        ...
        
    @abstractmethod
    async def close(self) -> None:
        """Cleans up any active connections (e.g., httpx clients)."""
        ...
