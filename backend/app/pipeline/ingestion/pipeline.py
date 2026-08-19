import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import aio_pika
import fitz
from app.config import settings
from app.messaging.connection import rabbitmq_manager
from app.pipeline.chunking.base import BaseChunker
from app.pipeline.chunking.fixed_chunker import FixedChunker
from app.pipeline.chunking.recursive_chunker import RecursiveChunker
from app.pipeline.cleaning.base import BaseCleaner
from app.pipeline.cleaning.text_cleaner import TextCleaner
from app.pipeline.detector.models import DocumentVisualJobMessage
from app.pipeline.detector.visual_detector import VisualRichDetector
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
        visual_detector: VisualRichDetector | None = None,
    ):
        self.cleaner = cleaner or TextCleaner()
        if chunker is not None:
            self.chunker = chunker
        elif settings.chunking_strategy == "recursive":
            self.chunker = RecursiveChunker()
        else:
            self.chunker = FixedChunker()
        self.embedder = embedder or OllamaEmbedder()
        self.indexer = indexer or CompositeIndexer()
        self.visual_detector = visual_detector or VisualRichDetector()

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
            # 1. Extraction (Standard Text Pass)
            extractor = ExtractorFactory.create(file_path)
            extraction = await self._run_stage(
                stage_name="extraction",
                action=lambda: extractor.extract(file_path),
                error_cls=ExtractionError,
                error_msg=f"Failed extracting '{file_path}'.",
                benchmark=benchmark,
            )

            # 1.5 Visual Detection & Routing (Only applies to PDFs)
            if str(file_path).lower().endswith(".pdf"):
                visual_jobs_count = await self._run_stage(
                    stage_name="visual_detection",
                    action=lambda: self._detect_and_queue_visuals(
                        document_id, file_path
                    ),
                    error_cls=ExtractionError,  # Grouping with extraction failures
                    error_msg="Failed visual detection and routing.",
                    benchmark=benchmark,
                )
                if visual_jobs_count > 0:
                    IngestionLogger.info(
                        f"Queued {visual_jobs_count} visual pages for {document_id}"
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
                toc=extraction.toc,
            )

        except IngestionError as exc:
            IngestionLogger.error(f"Ingestion failed for doc {document_id}: {exc}")
            raise

    async def _detect_and_queue_visuals(self, document_id: str, file_path: str) -> int:
        """Queue each visually rich PDF page for asynchronous processing."""
        doc = fitz.open(file_path)
        visual_jobs = []

        for page in doc:
            detection = self.visual_detector.analyze_page(page)
            if detection.should_process_visual:
                visual_jobs.append(
                    DocumentVisualJobMessage(
                        document_id=document_id,
                        page_number=detection.page_number,
                        classification=detection.classification,
                        reasons=detection.reasons,
                        signals=detection.signals.model_dump(),
                    )
                )
        doc.close()

        if visual_jobs:
            pool = rabbitmq_manager.get_channel_pool()
            async with pool.acquire() as channel:
                await channel.declare_queue("document.visual.queue", durable=True)
                for job in visual_jobs:
                    await channel.default_exchange.publish(
                        aio_pika.Message(
                            body=job.model_dump_json().encode(),
                            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                        ),
                        routing_key="document.visual.queue",
                    )

        return len(visual_jobs)

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
