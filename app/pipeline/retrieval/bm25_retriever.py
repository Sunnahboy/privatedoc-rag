from typing import Self

from app.config import settings

from ..indexing.tantivy_index import TantivyIndex
from .exceptions import RetrievalError
from .interface import BaseRetriever
from .models import RetrievalResult


class BM25Retriever(BaseRetriever):
    def __init__(
        self,
        index: TantivyIndex | None = None,
    ):
        self.index = index or TantivyIndex()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        document_id: str | None = None,
    ) -> RetrievalResult:
        if not query.strip():
            raise RetrievalError("Query cannot be empty")

        limit = top_k or settings.top_k_search

        chunks = await self.index.search(
            query=query,
            top_k=limit,
        )

        if document_id:
            chunks = [chunk for chunk in chunks if chunk.document_id == document_id]

        return RetrievalResult(
            chunks=chunks,
            found=bool(chunks),
            message=None if chunks else "No matching chunks found.",
        )

    async def close(self):
        await self.index.close()
