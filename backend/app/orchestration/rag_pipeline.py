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
from app.models.chat import ChatMessage
from typing import AsyncGenerator
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
        chat_history: list[ChatMessage] | None = None,
    ) -> GenerateResult:
        reset_profiler()
        rendered_images = []
        # Initialize metric trackers with safe defaults
        dense_count = 0
        sparse_count = 0
        visual_count = 0

        with profile("Retrieval"):
            if self.multimodal_pipeline and document_id:
                multimodal_result = await self.multimodal_pipeline.search(
                    query=question,
                    document_id=document_id,
                )
                dense_count = multimodal_result.dense_hits
                sparse_count = multimodal_result.sparse_hits
                visual_count = len(multimodal_result.visual_pages)
                logger.info(
                    "Visual search result | has_strong_visual_match: %s | visual_pages: %s",
                    multimodal_result.has_strong_visual_match,
                    [vp["page_number"] for vp in multimodal_result.visual_pages],
                    )
                retrieved = RetrievalResult(
                    chunks=multimodal_result.fused_chunks,
                    found=bool(multimodal_result.fused_chunks),
                    dense_hits=dense_count,
                    sparse_hits=sparse_count,
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
                                pix = page.get_pixmap(matrix=fitz.Matrix(1.2, 1.2))
                                
                                
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
                dense_count = retrieved.dense_hits
                sparse_count = retrieved.sparse_hits
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
                chat_history=chat_history,
            )
        timings = get_timings()
        log_rag_profile(
            timings=timings,
            dense_hits=dense_count,
            sparse_hits=sparse_count,
            visual_hits=visual_count,
            fused_hits=len(retrieved.chunks),
            context_chunks=len(retrieved.chunks),
            context_chars=sum(len(chunk.text) for chunk in retrieved.chunks),
            prompt_chars=result.prompt_chars,
        )

        return result
   

    async def ask_stream(
        self,
        question: str,
        document_ids: list[str],
        chat_history: list[ChatMessage] | None = None,
    ) -> AsyncGenerator[dict, None]:
        
        reset_profiler()
        rendered_images = []
        dense_count = 0
        sparse_count = 0
        visual_count = 0

        # Yield a status update so the UI knows we are working
        yield {
            "type": "status",
            "message": "Searching document vectors..."
        }

        with profile("Retrieval"):
            # Prevent context dilution and protect the CPU reranker
            base_k = 15
            dynamic_top_k = min(base_k + max(0, len(document_ids) - 1) * 5, 40)
            if self.multimodal_pipeline and document_ids:
                multimodal_result = await self.multimodal_pipeline.search(
                    query=question,
                    document_ids=document_ids,
                    text_top_k=dynamic_top_k,
                    final_top_k=8,
                )
                dense_count = multimodal_result.dense_hits
                sparse_count = multimodal_result.sparse_hits
                visual_count = len(multimodal_result.visual_pages)
                
                logger.info(
                    "Visual search result | has_strong_visual_match: %s | visual_pages: %s",
                    multimodal_result.has_strong_visual_match,
                    [vp["page_number"] for vp in multimodal_result.visual_pages],
                )
                
                retrieved = RetrievalResult(
                    chunks=multimodal_result.fused_chunks,
                    found=bool(multimodal_result.fused_chunks),
                    dense_hits=dense_count,
                    sparse_hits=sparse_count,
                    fused_hits=len(multimodal_result.fused_chunks),
                )

                if multimodal_result.has_strong_visual_match:
                    yield {
                        "type": "status",
                        "message": f"Extracting {visual_count} relevant visual pages..."
                    }
                    
                    pdf_path = Path(settings.upload_dir) / f"{document_ids}.pdf"
                    if pdf_path.exists():
                        with fitz.open(pdf_path) as doc:
                            for vp in multimodal_result.visual_pages:
                                # Safely extract the origin document for THIS specific image
                                origin_doc_id = vp.get("document_id") or document_ids[0]
                                pdf_path = Path(settings.upload_dir) / f"{origin_doc_id}.pdf"
                                
                                if pdf_path.exists():
                                    try:
                                        with fitz.open(pdf_path) as doc:
                                            page_num = vp["page_number"]
                                            if 0 < page_num <= len(doc):
                                                page = doc[page_num - 1] 
                                                pix = page.get_pixmap(matrix=fitz.Matrix(1.2, 1.2))
                                                img = Image.frombytes(
                                                    "RGBA" if pix.alpha else "RGB", 
                                                    [pix.width, pix.height], 
                                                    pix.samples
                                                )
                                                rendered_images.append(img)
                                    except Exception as e:
                                        logger.error(f"Failed to render page {page_num} for doc {origin_doc_id}: {e}")
            else:
                retrieved = await self.retriever.retrieve(
                    query=question,
                    document_id=document_ids[0] if document_ids else None,
                )
                dense_count = retrieved.dense_hits
                sparse_count = retrieved.sparse_hits

        # Handle empty results gracefully through the stream
        if not retrieved.found:
            yield {
                "type": "token", 
                "content": "I couldn't find any relevant information in the selected document."
            }
            yield {
                "type": "done",
                "citations": [],
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "prompt_chars": 0
            }
            return

        yield {
            "type": "status",
            "message": "Drafting response..."
        }

        with profile("Generation"):
            async for chunk in self.generator.generate_stream(
                question=question,
                context=retrieved.chunks,
                images=rendered_images if rendered_images else None,
                chat_history=chat_history,
            ):
                # When generation finishes, log our profiler metrics before sending the final chunk
                if chunk["type"] == "done":
                    timings = get_timings()
                    log_rag_profile(
                        timings=timings,
                        dense_hits=dense_count,
                        sparse_hits=sparse_count,
                        visual_hits=visual_count,
                        fused_hits=len(retrieved.chunks),
                        context_chunks=len(retrieved.chunks),
                        context_chars=sum(len(c.text) for c in retrieved.chunks),
                        prompt_chars=chunk.get("prompt_chars", 0),
                    )
                
                # Yield the token or done chunk up to the router
                yield chunk
    async def close(self):
        await self.retriever.close()
        await self.generator.close()
        if self.multimodal_pipeline and hasattr(self.multimodal_pipeline, "close"):
            await self.multimodal_pipeline.close()
