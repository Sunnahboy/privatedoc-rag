from dataclasses import dataclass
from typing import Any

from app.pipeline.retrieval.models import RetrievedChunk
from app.pipeline.retrieval.multimodal_retriever import MultimodalRetriever

from .flashrank_reranker import FlashRankReranker

# app/pipeline/retrieval/fusion/__init__.py
from .fusion.rrf import RRFFusion

__all__ = ["RRFFusion"]


@dataclass
class UnifiedRetrievalResult:
    text_chunks: list[RetrievedChunk]
    visual_pages: list[dict[str, Any]]
    fused_chunks: list[
        RetrievedChunk
    ]  # Fused chunks (both text and pseudo-visual chunks)
    fused_page_ranks: list[tuple[int, float]]
    has_strong_visual_match: bool  # Flag for the generator


class MultimodalRetrievalPipeline:
    def __init__(
        self,
        retriever: MultimodalRetriever,
        reranker: FlashRankReranker | None = None,
        fusion_engine: RRFFusion | None = None,
        visual_score_threshold: float = 12.0,  # Minimum ColQwen MaxSim score
    ):
        self.retriever = retriever
        self.reranker = reranker or FlashRankReranker()
        self.fusion = fusion_engine or RRFFusion()
        self.visual_score_threshold = visual_score_threshold

    async def search(
        self,
        query: str,
        document_id: str,
        text_top_k: int = 15,
        visual_top_k: int = 3,
        final_top_k: int = 5,
    ) -> UnifiedRetrievalResult:
        # 1. Parallel search in Qdrant
        raw_results = await self.retriever.retrieve(
            query=query,
            document_id=document_id,
            limit=max(text_top_k, visual_top_k),
        )

        # 2. Rerank text chunks via FlashRank
        raw_chunks = [
            RetrievedChunk(
                chunk_id=f"{document_id}_text_{idx}",
                document_id=document_id,
                text=item["text"],
                page_number=item["page_number"],
                score=item["score"],
                chunk_index=idx,
            )
            for idx, item in enumerate(raw_results["text_chunks"])
        ]
        reranked_chunks = self.reranker.rerank(
            query=query,
            chunks=raw_chunks,
            top_k=final_top_k,
        )

        # 3. Filter visual pages by threshold
        valid_visual_pages = [
            vp
            for vp in raw_results["visual_pages"]
            if vp.get("score", 0.0) >= self.visual_score_threshold
        ][:visual_top_k]

        has_strong_visual_match = len(valid_visual_pages) > 0

        # Transform visual page hits into pseudo-RetrievedChunks for RRFFusion
        visual_chunks = [
            RetrievedChunk(
                chunk_id=f"{document_id}_visual_page_{vp['page_number']}",
                document_id=document_id,
                chunk_index=vp['page_number'],
                text=f"[Visual Asset: Page {vp['page_number']} - Reasons: {vp.get('reasons', [])}]",
                page_number=vp['page_number'],
                score=vp['score'],
            )
            for vp in valid_visual_pages
        ]

        # 4. RRFFusion Integration (Combines text chunks and visual page tokens cleanly)
        fused_chunks = self.fusion.fuse(reranked_chunks, visual_chunks)[:final_top_k]

        # Derive aggregated page ranks from the fused output for easy context rendering
        page_rrf_scores: dict[int, float] = {}
        for chunk in fused_chunks:
            if chunk.page_number is not None:
                page_rrf_scores[chunk.page_number] = (
                    page_rrf_scores.get(chunk.page_number, 0.0) + chunk.score
                )

        sorted_pages = sorted(
            page_rrf_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        return UnifiedRetrievalResult(
            text_chunks=reranked_chunks,
            visual_pages=valid_visual_pages,
            fused_chunks=fused_chunks,
            fused_page_ranks=sorted_pages,
            has_strong_visual_match=has_strong_visual_match,
        )
