from typing import Self

from .bm25_retriever import BM25Retriever
from .fusion.rrf import RRFFusion
from .interface import BaseRetriever
from .models import RetrievalResult
from .qdrant_retriever import QdrantRetriever


class HybridRetriever(BaseRetriever):
    def __init__(
        self,
        dense: QdrantRetriever | None = None,
        sparse: BM25Retriever | None = None,
        fusion: RRFFusion | None = None,
    ):
        self.dense = dense or QdrantRetriever()
        self.sparse = sparse or BM25Retriever()
        self.fusion = fusion or RRFFusion()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        await self.dense.close()
        await self.sparse.close()

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        document_id: str | None = None,
    ) -> RetrievalResult: ...
