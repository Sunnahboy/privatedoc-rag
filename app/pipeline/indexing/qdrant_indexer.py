from app.config import settings
from app.pipeline.embeddings.models import EmbeddingResult
from qdrant_client import AsyncQrantClient

from .interface import BaseIndexer
from .models import IndexingResult


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

        self.client = AsyncQrantClient(
            url=self.url,
            api_key=self.api_key,
        )

    async def close(self) -> None:
        """Close the Qdrant client"""
        await self.client.close()

    async def index(
        self,
        embeddings: list[EmbeddingResult],
    ) -> IndexingResult: ...
