from abc import ABC, abstractmethod

from app.pipeline.retrieval.models import RetrievedChunk


class BaseFusion(ABC):
    @abstractmethod
    def fuse(
        self,
        *rankings: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        """Merge multiple ranked retrieval results."""
