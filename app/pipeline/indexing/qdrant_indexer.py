import asyncio

from app.config import settings
from app.pipeline.embeddings.models import EmbeddingResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from .exceptions import CollectionError, UpsertError
from .interface import BaseIndexer
from .models import IndexingResult


class QdrantIndexer(BaseIndexer):
    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        collection_name: str | None = None,
        batch_size: int | None = None,
    ) -> None:
        self.url = url or settings.qdrant_url
        self.api_key = api_key or settings.qdrant_api_key
        self.collection_name = collection_name or settings.qdrant_collection_name
        self.batch_size = batch_size or settings.qdrant_batch_size

        self.client = AsyncQdrantClient(
            url=self.url,
            api_key=self.api_key,
        )

    async def close(self) -> None:
        """Close the Qdrant client"""
        await self.client.close()

    async def ensure_collection(
        self,
        vector_size: int,
    ) -> None:
        """Create the collection if it does not exist."""
        try:
            exists = await self.client.collection_exists(
                collection_name=self.collection_name,
            )
            if exists:
                return
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    distance=Distance.COSINE,
                ),
            )
        except Exception as exc:
            raise CollectionError(
                f"Failed to ensure collection {self.collection_name}"
            ) from exc

    def _to_point(
        self,
        embeddings: EmbeddingResult,
    ) -> PointStruct:
        return PointStruct(
            id=str(embeddings.chunk_id),
            vector=embeddings.vector,
            payload={
                "document_id": str(embeddings.document_id),
                "chunk_index": embeddings.chunk_index,
                "model_name": embeddings.model_name,
            },
        )

    def _split_batches(
        self,
        points: list[PointStruct],
        batch_size: int = settings.qdrant_batch_size,
    ) -> list[list[PointStruct]]:
        return [points[i : i + batch_size] for i in range(0, len(points), batch_size)]

    async def _upsert_batch(
        self,
        batch: list[PointStruct],
    ) -> None:
        await self.client.upsert(
            collection_name=self.collection_name,
            points=batch,
            wait=True,
        )

    async def index(
        self,
        embeddings: list[EmbeddingResult],
    ) -> IndexingResult:
        if not embeddings:
            return IndexingResult(
                indexed_count=0,
                collection_name=self.collection_name,
            )

        await self.ensure_collection(
            vector_size=embeddings[0].dimensions,
        )

        points = [self._to_point(embedding) for embedding in embeddings]
        batches = self._split_batches(points)

        tasks = [self._upsert_batch(batch) for batch in batches]
        try:
            await asyncio.gather(*tasks)
        except Exception as exc:
            raise UpsertError(f"Failed to index {len(points)} points.") from exc
        return IndexingResult(
            indexed_count=len(points),
            collection_name=self.collection_nam,
        )
