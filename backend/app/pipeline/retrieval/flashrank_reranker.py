from flashrank import Ranker, RerankRequest

from app.config import settings
from app.pipeline.retrieval.models import RetrievedChunk

from .interface import BaseReranker


class FlashRankReranker(BaseReranker):
    def __init__(self):
        """
        Initializes the ONNX-based cross-encoder once at startup.

        WHY:
        - Hardcoding model names or paths in the class breaks the 12-Factor App methodology.
        - By pulling exclusively from `settings`, you can change models or cache directories
          via .env without ever touching application logic.
        """
        # The Truth: The class should not guess what model to use. It obeys the config.
        self.model_name = settings.reranker_model

        # Initialize the ONNX session once using explicit config paths
        self.ranker = Ranker(
            model_name=self.model_name, cache_dir=settings.reranker_cache_dir
        )

        # Match the exact property name from your Settings class
        self.top_k = settings.top_k_reranker

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        """
        Scores and sorts the retrieved chunks using a cross-encoder.
        """
        if not chunks:
            return []

        limit = top_k if top_k is not None else self.top_k

        # 1. TRUNCATE CANDIDATES
        # CS Principle: Bounding O(N). Cross-encoders are too heavy to run on the entire vector space.
        # We enforce a hard ceiling injected directly from the configuration.
        candidate_chunks = chunks[: settings.reranker_max_candidates]

        # 2. FORMAT PASSAGES WITH SAFE LENGTH CAP
        # CS Principle: Bounding O(L^2). Transformer self-attention scales quadratically with sequence length.
        # If a chunk is unexpectedly 10,000 characters, it will crash the CPU thread. The config cap prevents this.
        passages = [
            {
                "id": chunk.chunk_id,
                "text": chunk.text[: settings.reranker_max_chars] if chunk.text else "",
                "meta": {},
            }
            for chunk in candidate_chunks
        ]

        # 3. RUN BATCHED ONNX INFERENCE
        request = RerankRequest(query=query, passages=passages)
        reranked_results = self.ranker.rerank(request)

        # 4. MAP BACK TO DOMAIN MODELS
        # Fast O(1) dictionary lookup to map the bare ONNX results back to your rich Pydantic models
        chunk_lookup = {chunk.chunk_id: chunk for chunk in candidate_chunks}
        reranked_chunks = []

        for result in reranked_results[:limit]:
            original_chunk = chunk_lookup.get(result["id"])
            if not original_chunk:
                continue

            # Clone to maintain pure functions and avoid mutating shared state references
            updated_chunk = (
                original_chunk.model_copy()
                if hasattr(original_chunk, "model_copy")
                else original_chunk
            )
            updated_chunk.score = float(result["score"])
            reranked_chunks.append(updated_chunk)

        return reranked_chunks
