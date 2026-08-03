import asyncio
from typing import Self

from app.config import settings

from .bm25_retriever import BM25Retriever
from .exceptions import RetrievalError
from .fusion.rrf import RRFFusion
from .interface import BaseRetriever
from .models import RetrievalResult
from .qdrant_retriever import QdrantRetriever


class HybridRetriever(BaseRetriever):
    def __init__(
        self,
        dense: QdrantRetriever,
        sparse: BM25Retriever,
        fusion: RRFFusion | None = None,
    ):
        """Ensure configuration is decoupled."""
        self.dense = dense
        self.sparse = sparse
        self.fusion = fusion or RRFFusion()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        # handle close execution if retriever share resources
        await asyncio.gather(
            self.dense.close(),
            self.sparse.close(),
            # return_exceptions=True,
        )

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        document_id: str | None = None,
    ) -> RetrievalResult:
        if not query or not query.strip():
            raise RetrievalError("Query cannot be empty")
        limit = top_k or settings.top_k_search
        if limit <= 0:
            raise RetrievalError("top_k must be greater than zero")
        # Retrieve more candidates so RRF has a richer set to merge.
        candidate_limit = limit * settings.hybrid_candidate_multiplier

        dense_result, self.sparse_result = await asyncio.gather(
            self.dense.retrieve(
                query=query,
                top_k=candidate_limit,
                document_id=document_id,
            ),
            self.sparse.retrieve(
                query=query,
                top_k=candidate_limit,
                document_id=document_id,
            ),
        )
        # Execute reciprocal rank fusion over the enriched candidate sets
        fused_chunks = self.fusion.fuse(
            dense_result.chunks,
            self.sparse_result.chunks,
        )

        return RetrievalResult(
            chunks=fused_chunks[:limit],
            found=bool(fused_chunks),
            message=None if fused_chunks else "No matching chunks found.",
        )
