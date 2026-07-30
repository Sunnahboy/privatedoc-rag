from abc import ABC, abstractmethod

from app.pipeline.embeddings.models import EmbeddingResult

from .models import IndexingResult


class BaseIndexer(ABC):
    @abstractmethod
    async def index(
        self,
        embeddings: list[EmbeddingResult],
    ) -> IndexingResult:
        """ "
        Index embeddings into the vector database.
        """
        ...
