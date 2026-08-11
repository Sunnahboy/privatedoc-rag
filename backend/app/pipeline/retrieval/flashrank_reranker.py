from app.config import settings
from app.pipeline.retrieval.models import RetrievedChunk
from flashrank import Ranker, RerankRequest

from .interface import BaseReranker


class FlashRankReranker(BaseReranker):
    def __init__(
        self,
        model_name: str | None = None,
    ):
        """
        Initializes the ONNX-based cross-encoder.
        ms-marco-MiniLM-L-12-v2 is an excellent, lightweight default for RAG.
        """
        self.model_name = model_name or settings.reranker_model
        self.ranker = Ranker(model_name=self.model_name)
        
    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int | None = None, 
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []
        limit = top_k if top_k is not None else self.top_k
        

        # Format chunks into the dictionary structure FlashRank expects
        passages = [
            {"id": chunk.chunk_id, "text": chunk.text, "meta": {}} for chunk in chunks
        ]

        # Execute the cross-encoder scoring
        request = RerankRequest(query=query, passages=passages)
        reranked_results = self.ranker.rerank(request)

        # fast O(1) lookup dictionary for the original chunks
        chunk_lookup = {chunk.chunk_id: chunk for chunk in chunks}

        # Map the results back to your RetrievedChunk models
        reranked_chunks = []

        # FlashRank returns a sorted list of dicts with 'id', 'text', and 'score'
        for result in reranked_results[: limit]:
            # Locate the original chunk by ID to preserve your metadata
            original_chunk = chunk_lookup.get(result["id"])
            if not original_chunk:
                continue

            # Clone it to prevent mutating shared state
            updated_chunk = (
                original_chunk.model_copy()
                if hasattr(original_chunk, "model_copy")
                else original_chunk
            )
            updated_chunk.score = result["score"]

            reranked_chunks.append(updated_chunk)

        return reranked_chunks
