import asyncio

from fastembed import TextEmbedding

from app.config import settings
from app.pipeline.chunking.models import Chunk

from .base import BaseEmbedder
from .models import EmbeddingResult


class FastEmbedEmbedder(BaseEmbedder):
    """
    Generates dense embeddings directly in-process using ONNX Runtime on the CPU.
    Eliminates HTTP serialization overhead and prevents GPU VRAM thrashing.
    """

    def __init__(
        self,
        model_name: str | None = None,
        batch_size: int | None = None,
        threads: int | None = None,
    ) -> None:
        self.model_name = model_name or settings.embedding_model
        self.batch_size = batch_size or settings.embedding_batch_size

        # Limit threads so ONNX doesn't starve FastAPI's async event loop.
        # If None, it uses default CPU core heuristics.
        self.threads = threads

        self.model = TextEmbedding(model_name=self.model_name, threads=self.threads)

    async def embed_query(self, query: str) -> list[float]:
        """
        Embeds a single query vector in 10-30ms without touching the network or GPU.
        """
        # Use native query_embed(). FastEmbed automatically applies
        # the correct model-specific prefix (e.g., "query: ") under the hood.
        generator = await asyncio.to_thread(self.model.query_embed, query)
        vector = next(iter(generator))
        return vector.tolist()

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddingResult]:
        """
        Batch embeds chunks for document indexing directly in CPU memory.
        """
        if not chunks:
            return []

        texts = [chunk.text for chunk in chunks]

        # Use native embed(). FastEmbed automatically handles
        # document-side prefixes if the specific model requires them.
        generator = await asyncio.to_thread(
            self.model.embed, texts, batch_size=self.batch_size
        )

        vectors = [v.tolist() for v in generator]

        results: list[EmbeddingResult] = []
        for chunk, vector in zip(chunks, vectors, strict=True):
            results.append(
                EmbeddingResult(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    vector=vector,
                    model_name=self.model_name,
                    dimensions=len(vector),
                    page_number=chunk.page_number,
                    metadata={},
                )
            )
        return results

    async def close(self) -> None:
        """No-op: Satisfies BaseEmbedder interface as no network sockets exist."""
