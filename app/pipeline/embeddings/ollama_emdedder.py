from app.pipeline.chunking.models import Chunk

from .base import BaseEmbedder
from .models import EmbeddingResult


class OllamaEmbedder(BaseEmbedder):
    """
    Generates embeddings using a local Ollama model.
    """

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddingResult]: ...

    async def _embed_text(
        self,
        text: str,
    ) -> list[float]: ...
