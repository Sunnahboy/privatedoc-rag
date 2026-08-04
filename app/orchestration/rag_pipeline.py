from app.pipeline.generation.interface import BaseGenerator
from app.pipeline.generation.models import GenerateResult
from app.pipeline.generation.ollama_generator import OllamaGenerator
from app.pipeline.retrieval.bm25_retriever import BM25Retriever
from app.pipeline.retrieval.hybrid_retriever import HybridRetriever
from app.pipeline.retrieval.interface import BaseRetriever
from app.pipeline.retrieval.qdrant_retriever import QdrantRetriever
from app.utils.logging_utils import log_rag_profile
from app.utils.profiler import get_timings, profile, reset_profiler

from .base import BaseRAGPipeline


class RAGPipeline(BaseRAGPipeline):
    """Acts as a coordinator of the full workflow: retrieve context, generate a response and then shut everything down cleanly."""

    def __init__(
        self,
        retriever: BaseRetriever | None = None,
        generator: BaseGenerator | None = None,
    ):
        if retriever is None:
            retriever = HybridRetriever(
                dense=QdrantRetriever(),
                sparse=BM25Retriever(),
            )

        self.retriever = retriever
        self.generator = generator or OllamaGenerator()

    async def ask(
        self,
        question: str,
    ) -> GenerateResult:
        reset_profiler()
        with profile("Retrieval"):
            retrieved = await self.retriever.retrieve(
                query=question,
            )
        with profile("Generation"):
            result = await self.generator.generate(
                question=question,
                context=retrieved.chunks,
            )
        timings = get_timings()
        log_rag_profile(
            timings=timings,
            context_chunks=len(retrieved.chunks),
        )

        return result

    async def close(self):
        await self.retriever.close()
        await self.generator.close()
