from app.config import settings
from qdrant_client import AsyncQdrantClient

from .interface import BaseRetriever
from .models import RetrieveResult


class QdrantRetriever(BaseRetriever):
    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        collection_name: str | None = None,
    ) -> None:
        self.url = url or settings.qdrant_url
        self.api_key = api_key or settings.qdrant_url
        self.collection_name = collection_name or settings.qdrant_collection_name

        self.client = AsyncQdrantClient(
            url=self.url,
            api_key=self.api_key,
        )

    async def close(self) -> None:
        await self.client.close()

    async def retrieve(
        self, query: str, top_k: int | None = None
    ) -> RetrieveResult: ...
