from typing import Self

from app.config import settings

from ..indexing.tantivy_indexer import TantivyIndexer
from .exceptions import RetrievalError
from .interface import BaseRetriever
from .models import RetrievalResult


class BM25Retriever(BaseRetriever):
    def __init__(
        self,
        index: TantivyIndexer | None = None,
    ):
        self.index = index or TantivyIndexer()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def retrieve(
        self,
        query: str,
        user_id: str,
        top_k: int | None = None,
        document_id: str | None = None,
        document_ids: list[str] | None = None,
    ) -> RetrievalResult:
        if not query.strip():
            raise RetrievalError("Query cannot be empty")
        if not user_id or not user_id.strip():
            raise RetrievalError("user_id cannot be empty")

        limit = top_k or settings.top_k_search
        if limit <= 0:
            raise RetrievalError("top_k must be greater than zero")

        # The Tantivy layer accepts a document-id list. Retain the original
        # singular argument as a compatibility path rather than dropping its
        # filter when a caller searches one document.
        scoped_document_ids = list(document_ids or [])
        if document_id and document_id not in scoped_document_ids:
            scoped_document_ids.append(document_id)

        chunks = await self.index.search(
            query=query,
            top_k=limit,
            # Tantivy builds a literal `(user_id:"...") AND (...)` clause.
            user_id=user_id,
            document_ids=scoped_document_ids or None,
        )

        return RetrievalResult(
            chunks=chunks,
            found=bool(chunks),
            message=None if chunks else "No matching chunks found.",
        )

    async def close(self):
        await self.index.close()
