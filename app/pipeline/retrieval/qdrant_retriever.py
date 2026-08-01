from typing import Self

from app.config import settings
from app.pipeline.embeddings.base import BaseEmbedder
from app.pipeline.embeddings.ollama_emdedder import OllamaEmbedder
from qdrant_client import AsyncQdrantClient

from .exceptions import RetrievalError, SearchError
from .interface import BaseRetriever
from .models import RetrievalResult, RetrievedChunk


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

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def _embed_query(
        self,
        query: str,
    ) -> list[float]:
        """Convert a user query into an embedding vector."""
        return await self.embedder.embed_query(query)

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
        query_vector = await self._embed_query(query)

        try:
            response = await self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=limit,
                with_payload=True,
            )

            chunks = [
                RetrievedChunk(
                    chunk_id=str(point.id),
                    document_id=point.payload["document_id"],
                    chunk_index=point.payload["chunk_index"],
                    text=point.payload["text"],
                    score=point.score,
                )
                for point in response.points
            ]
        except Exception as exc:
            raise SearchError("Vector search failed.") from exc

        return RetrievalResult(chunks=chunks)
