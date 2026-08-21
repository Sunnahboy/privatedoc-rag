import asyncio
from typing import Self
import uuid
from app.config import settings
from app.pipeline.embeddings.models import EmbeddingResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)
import logging
from .exceptions import CollectionError, UpsertError
from .interface import BaseIndexer
from .models import IndexingRequest, IndexingResult
logger = logging.getLogger(__name__)

class QdrantIndexer(BaseIndexer):
    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        collection_name: str | None = None,
        visual_collection_name: str | None = None,
        batch_size: int | None = None,
        max_concurrent_requests: int | None = None,
    ) -> None:
        self.url = url or settings.qdrant_url
        self.api_key = api_key or settings.qdrant_api_key
        self.collection_name = collection_name or settings.qdrant_collection_name
        self.visual_collection_name = visual_collection_name or getattr(
            settings, "qdrant_visual_collection_name", "documents_visual"
        )
        self.batch_size = batch_size or settings.qdrant_batch_size
        self.max_concurrent_requests = asyncio.Semaphore(
            max_concurrent_requests or settings.qdrant_max_concurrent_requests
        )

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
                    size=vector_size,
                    distance=Distance.COSINE,
                ),
            )
        except Exception as exc:
            raise CollectionError(
                f"Failed to ensure collection {self.collection_name}"
            ) from exc

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    def _to_point(
        self,
        embedding: EmbeddingResult,
    ) -> PointStruct:
        qdrant_id = str(uuid.uuid5(uuid.NAMESPACE_OID, str(embedding.chunk_id)))
        return PointStruct(
            id=qdrant_id,
            vector=embedding.vector,
            payload={
                "original_chunk_id": str(embedding.chunk_id),
                "document_id": str(embedding.document_id),
                "chunk_index": embedding.chunk_index,
                "page_number": embedding.page_number,
                "text": embedding.text,
                "model_name": embedding.model_name,
            },
        )

    def _split_batches(
        self,
        points: list[PointStruct],
    ) -> list[list[PointStruct]]:
        size = self.batch_size
        return [points[i : i + size] for i in range(0, len(points), size)]

    async def _upsert_batch(
        self,
        batch: list[PointStruct],
    ) -> None:
        async with self.max_concurrent_requests:
            await self.client.upsert(
                collection_name=self.collection_name,
                points=batch,
                wait=True,
            )

    async def index(
        self,
        request: IndexingRequest,
    ) -> IndexingResult:
        embeddings = request.embeddings

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
            collection_name=self.collection_name,
        )

    async def delete_document(
        self,
        document_id: str,
    ) -> None:
        """Delete all text vectors and visual vectors belonging to a document."""
        delete_filter = Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_id),
                )
            ]
        )

        async def _delete_from_collection(collection: str):
            try:
                # Check if collection exists first so we don't crash if one is missing
                if await self.client.collection_exists(collection):
                    await self.client.delete(
                        collection_name=collection,
                        points_selector=delete_filter,
                        wait=True,
                    )
                    logger.info(f"Successfully deleted document '{document_id}' from '{collection}'.")
            except Exception as e:
                logger.error(
                    f"Failed to delete document '{document_id}' from '{collection}': {e}", 
                    exc_info=True
                )

        await asyncio.gather(
            _delete_from_collection(self.collection_name),
            _delete_from_collection(self.visual_collection_name)
        )
