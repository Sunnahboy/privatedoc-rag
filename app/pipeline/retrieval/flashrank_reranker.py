from app.pipeline.retrieval.models import RetrievedChunk
from flashrank import Ranker, RerankRequest

from .interface import BaseReranker


class FlashRankReranker(BaseReranker):
    def __init__(self, model_name: str = "ms-marco-MiniLM-L-12-v2"):
        """
        Initializes the ONNX-based cross-encoder.
        ms-marco-MiniLM-L-12-v2 is an excellent, lightweight default for RAG.
        """
        self.ranker = Ranker(model_name=model_name)

    def rerank(
        self, query: str, chunks: list[RetrievedChunk], top_k: int = 5
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []

        # 1. Format chunks into the dictionary structure FlashRank expects
        passages = [
            {"id": chunk.chunk_id, "text": chunk.text, "meta": {}} for chunk in chunks
        ]

        # 2. Execute the cross-encoder scoring
        request = RerankRequest(query=query, passages=passages)
        reranked_results = self.ranker.rerank(request)

        # 3. Map the results back to your RetrievedChunk models
        reranked_chunks = []

        # FlashRank returns a sorted list of dicts with 'id', 'text', and 'score'
        for result in reranked_results[:top_k]:
            # Locate the original chunk by ID to preserve your metadata
            original_chunk = next(c for c in chunks if c.chunk_id == result["id"])

            # Clone it to prevent mutating shared state
            updated_chunk = (
                original_chunk.model_copy()
                if hasattr(original_chunk, "model_copy")
                else original_chunk
            )
            updated_chunk.score = result["score"]

            reranked_chunks.append(updated_chunk)

        return reranked_chunks
