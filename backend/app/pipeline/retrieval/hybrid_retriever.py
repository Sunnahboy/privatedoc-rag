import asyncio
from typing import Self

from app.config import settings
from app.utils.profiler import profile

from .bm25_retriever import BM25Retriever
from .exceptions import RetrievalError
from .flashrank_reranker import FlashRankReranker
from .fusion.rrf import RRFFusion
from .interface import BaseReranker, BaseRetriever
from .models import RetrievalResult
from .qdrant_retriever import QdrantRetriever


class HybridRetriever(BaseRetriever):
    def __init__(
        self,
        dense: QdrantRetriever,
        sparse: BM25Retriever,
        fusion: RRFFusion | None = None,
        reranker: BaseReranker | None = None,
    ):
        """Ensure configuration is decoupled."""
        self.dense = dense
        self.sparse = sparse
        self.fusion = fusion or RRFFusion()
        self.reranker = reranker or FlashRankReranker()

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
        limit: int = 5,  
        **kwargs
    ) -> RetrievalResult:
        if not query or not query.strip():
            raise RetrievalError("Query cannot be empty")
        if top_k is None:
            limit = settings.top_k_search
        else:
            limit = top_k

        if limit <= 0:
            raise RetrievalError("top_k must be greater than zero")

        if limit <= 0:
            raise RetrievalError("top_k must be greater than zero")
        # Retrieve more candidates so RRF has a richer set to merge.
        candidate_limit = limit * settings.hybrid_candidate_multiplier

        async def _dense_search():
            return await self.dense.retrieve(
                query=query,
                top_k=candidate_limit,
                document_id=document_id,
            )

        async def _sparse_search():
            with profile("Sparse Search"):
                return await self.sparse.retrieve(
                    query=query,
                    top_k=candidate_limit,
                    document_id=document_id,
                )

        with profile("Hybrid Retrieval"):
            dense_result, sparse_result = await asyncio.gather(
                _dense_search(),
                _sparse_search(),
            )

            with profile("RRF Fusion"):
                fused_chunks = self.fusion.fuse(
                    dense_result.chunks,
                    sparse_result.chunks,
                )

            with profile("Cross-Encoder Reranking"):
                # Pass the query, the broad fused chunks, and the final limit (e.g., 5)
                final_chunks = self.reranker.rerank(
                    query=query, chunks=fused_chunks, top_k=limit
                )

        return RetrievalResult(
            chunks=final_chunks,
            found=bool(final_chunks),
            message=None if fused_chunks else "No matching chunks found.",
            dense_hits=len(dense_result.chunks),
            sparse_hits=len(sparse_result.chunks),
            fused_hits=len(fused_chunks),
        )
