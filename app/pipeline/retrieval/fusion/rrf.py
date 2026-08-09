from collections import defaultdict

from app.pipeline.retrieval.models import RetrievedChunk

from .base import BaseFusion


class RRFFusion(BaseFusion):
    def __init__(
        self,
        k: int = 60,
    ):
        self.k = k

    def fuse(
        self,
        *rankings: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        scores: dict[str, float] = defaultdict(float)
        chunk_lookup: dict[str, RetrievedChunk] = {}

        for ranking in rankings:
            for rank, chunk in enumerate(ranking, start=1):
                if chunk.chunk_id not in chunk_lookup:
                    # copy the chunk so  don't mutate the original object
                    # in case it's being used elsewhere in memory.
                    chunk_lookup[chunk.chunk_id] = (
                        chunk.model_copy() if hasattr(chunk, "model_copy") else chunk
                    )

                # Reciprocal Rank Fusion score
                scores[chunk.chunk_id] += 1.0 / (self.k + rank)
        # Assign new fused score back to the chunk
        for chunk_id, fused_score in scores.items():
            chunk_lookup[chunk_id].score = fused_score

        # Sort by fused score (highest first)
        return sorted(
            chunk_lookup.values(),
            key=lambda chunk: scores[chunk.chunk_id],
            reverse=True,
        )
