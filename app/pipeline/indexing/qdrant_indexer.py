from app.config import settings
from app.pipeline.embedding.models import EmbeddingResult
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams,PointStruct

from .exceptions import CollectionError,UpsertError
from .interface import BaseIndexer
from .models import IndexingResult
from uiid import UIID



class QdrantIndexer(BaseIndexer):
    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        collection_name: str | None = None,
    ) -> None:
        self.url = url or settings.qdrant_url
        self.api_key = api_key or settings.qdrant_api_key
        self.collection_name = collection_name or settings.qdrant_collection_name

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
                embedding:EmbeddingResult,

        )->PointStruct:
            return PointStruct(
                id=str(embedding.chunk_id),
                vector=embedding.vector,
                payload={
                    "document_id":str(embedding.document_id),
                    "chunk_index":embedding.chunk_index,
                    "model_name":embedding.model_name,
                },
            )

        async def index(
            self,
            embedding: list[EmbeddingResult],
        ) -> IndexingResult:
            if not embedding:
                return IndexingResult(
                    indexed_count=0,
                    collection_name=self.collection_name,
                )

            await self.ensure_collection(
                vector_size=embedding[0].dimensions,
            )

            points = [
                self._to_point(embedding)
            ]
            raise NotImplementedError
