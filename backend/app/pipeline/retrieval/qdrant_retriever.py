from typing import Self

from qdrant_client import AsyncQdrantClient, models

from app.config import settings
from app.pipeline.embeddings.base import BaseEmbedder
from app.pipeline.embeddings.factory import create_embedder
from app.utils.profiler import profile

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
        self.embedder = embedder or create_embedder()

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

    async def retrieve(
        self,
        query: str,
        user_id: str,
        top_k: int | None = None,
        document_id: str | None = None,
        document_ids: list[str] | None = None,
    ) -> RetrievalResult:
        """
        Retrieve the top-k most relevant chunks for a query.
        """

        limit = top_k or settings.top_k_search
        if limit <= 0:
            raise RetrievalError("top_k must be greater than zero")
        if not query.strip():
            raise RetrievalError("Query cannot be empty")
        if not user_id or not user_id.strip():
            raise RetrievalError("user_id cannot be empty")

        # Keep compatibility with the single-document call path while
        # preserving the existing multi-document filter behavior.
        scoped_document_ids = list(document_ids or [])
        if document_id and document_id not in scoped_document_ids:
            scoped_document_ids.append(document_id)

        with profile("Query Embedding"):
            query_vector = await self._embed_query(query)

        try:
            # Tenant lock is unconditional. Qdrant applies every `must`
            # condition, so an optional document constraint can only narrow a
            # user's own corpus; it can never widen the tenant boundary.
            must_conditions: list[models.FieldCondition] = [
                models.FieldCondition(
                    key="user_id",
                    match=models.MatchValue(value=user_id),
                )
            ]
            if scoped_document_ids:
                must_conditions.append(
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchAny(any=scoped_document_ids),
                    )
                )
            query_filter = models.Filter(must=must_conditions)

            with profile("Qdrant Search"):
                response = await self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    query_filter=query_filter,
                    limit=limit,
                    with_payload=True,
                )

            chunks = []

            for point in response.points:
                if point.score < settings.retrieval_score_threshold:
                    continue
                payload = point.payload
                chunks.append(
                    RetrievedChunk(
                        chunk_id=str(point.id),
                        document_id=payload["document_id"],
                        chunk_index=payload["chunk_index"],
                        text=payload["text"],
                        score=point.score,
                        page_number=payload.get("page_number"),
                    )
                )
        except Exception as exc:
            raise SearchError("Vector search failed.") from exc
        if not chunks:
            return RetrievalResult(
                chunks=[],
                found=False,
                message="No relevant chunks found above the similarity threshold.",
            )

        return RetrievalResult(
            chunks=chunks,
            found=True,
        )
