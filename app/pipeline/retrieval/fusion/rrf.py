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
                # Keep one copy of each chunk
                chunk_lookup.setdefault(chunk.chunk_id, chunk)

                # Reciprocal Rank Fusion score
                scores[chunk.chunk_id] += 1.0 / (self.k + rank)

        # Sort by fused score (highest first)
        return sorted(
            chunk_lookup.values(),
            key=lambda chunk: scores[chunk.chunk_id],
            reverse=True,
        )
