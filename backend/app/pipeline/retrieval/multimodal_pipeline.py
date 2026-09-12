from dataclasses import dataclass
from typing import Any

from app.pipeline.retrieval.models import RetrievedChunk
from app.pipeline.retrieval.multimodal_retriever import MultimodalRetriever

from .flashrank_reranker import FlashRankReranker


@dataclass
class UnifiedRetrievalResult:
    text_chunks: list[RetrievedChunk]
    visual_pages: list[dict[str, Any]]
    fused_chunks: list[
        RetrievedChunk
    ]  # Fused chunks (both text and pseudo-visual chunks)
    fused_page_ranks: list[tuple[int, float]]
    has_strong_visual_match: bool  
    dense_hits: int = 0   
    sparse_hits: int = 0  


class MultimodalRetrievalPipeline:
    def __init__(
        self,
        retriever: MultimodalRetriever,
        reranker: FlashRankReranker | None = None,
        fusion_engine: FlashRankReranker | None = None,
        visual_score_threshold: float = 12.0,  # Minimum ColQwen MaxSim score
    ):
        self.retriever = retriever
        self.reranker = reranker or FlashRankReranker()
        self.fusion = fusion_engine or FlashRankReranker()
        self.visual_score_threshold = visual_score_threshold

    async def search(
        self,
        query: str,
        document_ids: list[str],
        user_id: str,  
        text_top_k: int = 20,
        visual_top_k: int = 2,
        final_top_k: int = 8,
    ) -> UnifiedRetrievalResult:
        # 1. Parallel search in Qdrant
        raw_results = await self.retriever.retrieve(
            query=query,
            document_ids=document_ids,
            user_id=user_id,
            limit=max(text_top_k, 10),
        )

        # 2. Rerank text chunks via FlashRank
        # 2. Rerank text chunks via FlashRank
        raw_chunks = [
            RetrievedChunk(
                # Safely extract the exact document_id from the Qdrant item payload
                chunk_id=f"{item.get('document_id', 'unknown')}_text_{idx}",
                document_id=item.get("document_id", "unknown"),
                text=item["text"],
                page_number=item.get("page_number"),
                score=item.get("score", 0.0),
                chunk_index=idx,
            )
            for idx, item in enumerate(raw_results.get("text_chunks", []))
        ]
        top_fused_chunks = raw_chunks[:text_top_k]
        reranked_chunks = self.reranker.rerank(
            query=query,
            chunks=top_fused_chunks,
            top_k=final_top_k,
        )

        # Filter and Sort Visual Pages (Keep only the absolute best 1 or 2)
        matched_visual_pages = [
            vp
            for vp in raw_results.get("visual_pages", [])
            if vp.get("score", 0.0) >= self.visual_score_threshold
        ]

        valid_visual_pages = sorted(
            matched_visual_pages,
            key=lambda x: x.get("score", 0.0),
            reverse=True,
        )[:visual_top_k]

        has_strong_visual_match = len(valid_visual_pages) > 0

       
        # assign the real text directly to fused_chunks. 
        fused_chunks = reranked_chunks

        # Derive aggregated page ranks for the UI based on the top 8 text chunks
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
            dense_hits=raw_results.get("dense_hits", 0),  
            sparse_hits=raw_results.get("sparse_hits", 0), 
        )
