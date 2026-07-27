from app.config import settings
from app.pipeline.chunking.models import Chunk

from .base import BaseEmbedder
from .models import EmbeddingResult


class OllamaEmbedder(BaseEmbedder):
    """
    Generates embeddings using a local Ollama model.
    """

    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url
        self.model = settings.embedding_model
        self.timeout = settings.embedding_timeout

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddingResult]: ...

    async def _embed_text(
        self,
        text: str,
    ) -> list[float]: ...
