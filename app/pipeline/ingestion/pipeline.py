import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from app.pipeline.chunking.base import BaseChunker
from app.pipeline.chunking.fixed_chunker import FixedChunker
from app.pipeline.cleaning.base import BaseCleaner
from app.pipeline.cleaning.text_cleaner import TextCleaner
from app.pipeline.embeddings.base import BaseEmbedder
from app.pipeline.embeddings.ollama_embedder import OllamaEmbedder
from app.pipeline.extraction.factory import ExtractorFactory
from app.pipeline.indexing.composite_indexer import CompositeIndexer
from app.pipeline.indexing.interface import BaseIndexer
from app.pipeline.indexing.models import IndexingRequest

from .base import BaseIngestionPipeline
from .exceptions import (
    ChunkingError,
    CleaningError,
    EmbeddingError,
    ExtractionError,
    IndexingError,
    IngestionError,
)
from .logger import IngestionLogger
from .models import IngestionResult


@dataclass
class IngestionBenchmark:
    """Strongly-typed container for pipeline stage metrics."""

    timings: dict[str, float] = field(default_factory=dict)
    total_elapsed: float = 0.0
    chunk_count: int = 0


class IngestionPipeline(BaseIngestionPipeline):
    def __init__(
        self,
        cleaner: BaseCleaner | None = None,
        chunker: BaseChunker | None = None,
        embedder: BaseEmbedder | None = None,
        indexer: BaseIndexer | None = None,
    ):
        self.cleaner = cleaner or TextCleaner()
        self.chunker = chunker or FixedChunker()
        self.embedder = embedder or OllamaEmbedder()
        self.indexer = indexer or CompositeIndexer()

    async def ingest(
        self,
        document_id: str,
        file_path: str,
    ) -> IngestionResult:
        if not document_id:
            raise IngestionError("Document ID cannot be empty.")
        if not file_path:
            raise IngestionError("File path cannot be empty.")

        benchmark = IngestionBenchmark()
        total_start = time.perf_counter()

        try:
            # 1. Extraction (Lightweight extractor, no manual close step)
            extractor = ExtractorFactory.create(file_path)
            extraction = await self._run_stage(
                stage_name="extraction",
                action=lambda: extractor.extract(file_path),
                error_cls=ExtractionError,
                error_msg=f"Failed extracting '{file_path}'.",
                benchmark=benchmark,
            )

            # 2. Cleaning
            cleaning = await self._run_stage(
                stage_name="cleaning",
                action=lambda: self.cleaner.clean(extraction),
                error_cls=CleaningError,
                error_msg="Failed cleaning extracted document.",
                benchmark=benchmark,
            )

            # 3. Chunking
            chunks = await self._run_stage(
                stage_name="chunking",
                action=lambda: self.chunker.chunk(cleaning),
                error_cls=ChunkingError,
                error_msg="Failed chunking cleaned document.",
                benchmark=benchmark,
            )

            # Chunk Decoration
            for index, chunk in enumerate(chunks):
                chunk.document_id = document_id
                chunk.chunk_index = index
            benchmark.chunk_count = len(chunks)

            # 4. Embedding
            embeddings = await self._run_stage(
                stage_name="embedding",
                action=lambda: self.embedder.embed(chunks),
                error_cls=EmbeddingError,
                error_msg="Failed generating embeddings.",
                benchmark=benchmark,
            )

            # 5. Indexing
            indexing_result = await self._run_stage(
                stage_name="indexing",
                action=lambda: self.indexer.index(
                    IndexingRequest(
                        chunks=chunks,
                        embeddings=embeddings,
                    )
                ),
                error_cls=IndexingError,
                error_msg="Failed indexing embeddings.",
                benchmark=benchmark,
            )

            benchmark.total_elapsed = time.perf_counter() - total_start

            # Delegate tracking directly to the logger interface
            IngestionLogger.benchmark(
                document_id=document_id,
                timings=benchmark.timings,
                total=benchmark.total_elapsed,
                chunks=benchmark.chunk_count,
            )
            return IngestionResult(
                indexing=indexing_result,
                total_chunks=benchmark.chunk_count,
                total_pages=extraction.total_pages,
            )

        except IngestionError as exc:
            IngestionLogger.error(f"Ingestion failed for doc {document_id}: {exc}")
            raise

    async def _run_stage(
        self,
        stage_name: str,
        action: Callable[[], Awaitable[Any]],
        error_cls: type[IngestionError],
        error_msg: str,
        benchmark: IngestionBenchmark,
    ) -> Any:
        """Helper to flatten try-except blocks and automatically record metrics."""
        start = time.perf_counter()
        try:
            result = await action()
            benchmark.timings[stage_name] = time.perf_counter() - start
            return result
        except Exception as exc:
            raise error_cls(error_msg) from exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def close(self) -> None:
        await self._close_component(self.cleaner)
        await self._close_component(self.chunker)
        await self._close_component(self.embedder)
        await self._close_component(self.indexer)

    async def _close_component(self, component: Any) -> None:
        if component is None:
            return
        close_method = getattr(component, "close", None)
        if callable(close_method):
            try:
                await close_method()
            except (RuntimeError, OSError) as exc:
                IngestionLogger.warning(
                    f"Resource cleanup issue in {component.__class__.__name__}: {exc}"
                )
