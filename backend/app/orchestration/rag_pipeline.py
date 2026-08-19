from app.pipeline.generation.interface import BaseGenerator
from app.pipeline.generation.models import GenerateResult
from app.pipeline.generation.ollama_generator import OllamaGenerator
from app.pipeline.retrieval.bm25_retriever import BM25Retriever
from app.pipeline.retrieval.hybrid_retriever import HybridRetriever
from app.pipeline.retrieval.interface import BaseRetriever
from app.pipeline.retrieval.models import RetrievalResult
from app.pipeline.retrieval.multimodal_pipeline import MultimodalRetrievalPipeline
from app.pipeline.retrieval.qdrant_retriever import QdrantRetriever
from app.utils.logging_utils import log_rag_profile
from app.utils.profiler import get_timings, profile, reset_profiler
from pathlib import Path
import fitz
from PIL import Image
from .base import BaseRAGPipeline
from app.config import settings
import logging

logger = logging.getLogger(__name__)
class RAGPipeline(BaseRAGPipeline):
    """Acts as a coordinator of the full workflow: retrieve context, generate a response and then shut everything down cleanly."""

    def __init__(
        self,
        retriever: BaseRetriever | None = None,
        generator: BaseGenerator | None = None,
        multimodal_pipeline: MultimodalRetrievalPipeline | None = None,
    ):
        if retriever is None:
            retriever = HybridRetriever(
                dense=QdrantRetriever(),
                sparse=BM25Retriever(),
            )

        self.retriever = retriever
        self.generator = generator or OllamaGenerator()
        self.multimodal_pipeline = multimodal_pipeline

    async def ask(
        self,
        question: str,
        document_id: str | None = None,
    ) -> GenerateResult:
        reset_profiler()
        rendered_images = []

        with profile("Retrieval"):
            if self.multimodal_pipeline and document_id:
                multimodal_result = await self.multimodal_pipeline.search(
                    query=question,
                    document_id=document_id,
                )
                logger.info(
                    "Visual search result | has_strong_visual_match: %s | visual_pages: %s",
                    multimodal_result.has_strong_visual_match,
                    [vp["page_number"] for vp in multimodal_result.visual_pages],
                    )
                retrieved = RetrievalResult(
                    chunks=multimodal_result.fused_chunks,
                    found=bool(multimodal_result.fused_chunks),
                    dense_hits=len(multimodal_result.text_chunks),
                    fused_hits=len(multimodal_result.fused_chunks),
                )

                if multimodal_result.has_strong_visual_match:
                    pdf_path = Path(settings.upload_dir) / f"{document_id}.pdf"
    
                    if pdf_path.exists():
                        #Context manager ensures file safely closes if an exception triggers
                        with fitz.open(pdf_path) as doc:
                            for vp in multimodal_result.visual_pages:
                                page_num = vp["page_number"]
                                
                                #fitz uses 0-based indexing for pages
                                page = doc[page_num - 1] 
                                pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
                                
                                
                                img = Image.frombytes(
                                    "RGBA" if pix.alpha else "RGB", 
                                    [pix.width, pix.height], 
                                    pix.samples
                                )
                                rendered_images.append(img)
            else:
                retrieved = await self.retriever.retrieve(
                    query=question,
                    document_id=document_id,
                )
        if not retrieved.found:
            return GenerateResult(
                answer="I couldn't find any relevant information in the selected document.",
                citations=[],
                prompt_tokens=0,
                completion_tokens=0,
                prompt_chars=0,
            )
        with profile("Generation"):
            result = await self.generator.generate(
                question=question,
                context=retrieved.chunks,
                images=rendered_images if rendered_images else None,
            )
        timings = get_timings()
        log_rag_profile(
            timings=timings,
            dense_hits=retrieved.dense_hits,
            sparse_hits=retrieved.sparse_hits,
            fused_hits=retrieved.fused_hits,
            context_chunks=len(retrieved.chunks),
            context_chars=sum(len(chunk.text) for chunk in retrieved.chunks),
            prompt_chars=result.prompt_chars,
        )

        return result

    async def close(self):
        await self.retriever.close()
        await self.generator.close()
        if self.multimodal_pipeline and hasattr(self.multimodal_pipeline, "close"):
            await self.multimodal_pipeline.close()
