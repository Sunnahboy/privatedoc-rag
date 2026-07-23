from abc import ABC, abstractmethod

from app.pipeline.chunking.models import Chunk

from .models import EmbeddingResult


class BaseEmbedder(ABC):
    """
    Base interface for all embeddings providers.

    Every embedding implementation (OLLama, OpenAI, VoyageAI,
    SentenceTransformers, etc.) must implement this interface.

    """

    @abstractmethod
    async def embed(
        self,
        chunks: list[Chunk],
    ) -> list[EmbeddingResult]:
        """
        Generate embeddings for a list of chunks.

        Args:
            chunks: Chunks to embed.

        Returns:
            A list of EmbeddingResult objects.


        """
        ...
