from app.config import settings
from app.pipeline.embeddings.base import BaseEmbedder
from app.pipeline.embeddings.ollama_emdedder import OllamaEmbedder
from qdrant_client import AsyncQdrantClient

from .exceptions import RetrievalError
from .interface import BaseRetriever
from .models import RetrievalResult


class QdrantRetriever(BaseRetriever):
    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        collection_name: str | None = None,
        embedder: BaseEmbedder | None = None,
    ) -> None:
        self.url = url or settings.qdrant_url
        self.api_key = api_key or settings.qdrant_api_key
        self.collection_name = collection_name or settings.qdrant_collection_name
        self.embedder = embedder or OllamaEmbedder()

        self.client = AsyncQdrantClient(
            url=self.url,
            api_key=self.api_key,
        )

    async def __aenter__(self) -> "QdrantRetriever":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def _embed_query(
        self,
        query: str,
    ) -> list[float]:
        """Convert a user query into an embedding vector."""

    async def close(self) -> None:
        """Close underlying connections"""
        await self.client.close()

    async def retrieve(self, query: str, top_k: int | None = None) -> RetrievalResult:
        """
        Retrieve the top-k most relevant chunks for a query.
        """

        limit = top_k or settings.top_k_search
        if limit <= 0:
            raise RetrievalError("top_k must be greater than zero")
        if not query.strip():
            raise RetrievalError("Query cannot be empty")
