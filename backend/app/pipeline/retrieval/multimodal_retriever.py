import asyncio
import logging
from typing import Any

from app.config import settings
from app.pipeline.embeddings.base import BaseEmbedder
from app.pipeline.embeddings.visual_engine import VisualRetrieverEngine
from qdrant_client import AsyncQdrantClient, models
from app.pipeline.retrieval.hybrid_retriever import HybridRetriever
logger = logging.getLogger(__name__)


class MultimodalRetriever:
    def __init__(
        self,
        qdrant_client: AsyncQdrantClient,
        text_retriever: HybridRetriever,
        visual_engine: VisualRetrieverEngine,
        visual_collection: str | None = None,
    ):
        self.client = qdrant_client
        self.text_retriever= text_retriever
        self.visual_engine = visual_engine

        
        self.visual_collection = visual_collection or getattr(
            settings, "qdrant_visual_collection_name", "documents_visual"
        )

    async def retrieve(
        self, query: str, document_id: str, limit: int = 5
    ) -> dict[str, list[Any]]:
        """
        Executes parallel searches across both the text and visual collections.
        Filters by the specific document_id.
        """
        logger.info(f"Executing multimodal retrieval for query: '{query}'")

        
        # Hybrid Text Task (Handles dense, sparse, and reranking internally)
        text_task = self.text_retriever.retrieve(
            query=query, 
            top_k=limit, 
            document_id=document_id
        )
       # 2. Visual Task (Handles ColQwen2 encoding and Qdrant nearest-neighbor search)
        async def _visual_search():
            visual_vector = await asyncio.to_thread(self.visual_engine.embed_query, query)
            doc_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id", match=models.MatchValue(value=document_id)
                    )
                ]
            )
            response = await self.client.query_points(
                collection_name=self.visual_collection,
                query=models.NearestQuery(nearest=visual_vector.tolist()),
                query_filter=doc_filter,
                limit=limit,
            )
            return response.points

        
        # Execute both entirely different retrieval pipelines concurrently
        text_result, visual_results = await asyncio.gather(
            text_task, _visual_search()
        )

        

        
        
    # Format Text Chunks (RetrievedChunk domain models)
        formatted_text_chunks = [
            {
                "score": chunk.score,
                "text": chunk.text,
                "page_number": getattr(chunk, "page_number", None),
                "chunk_id": getattr(chunk, "chunk_id", None),
            }
            for chunk in getattr(text_result, "chunks", [])
        ]

        # Format Visual Pages (Qdrant ScoredPoint objects with payload)
        formatted_visual_pages = [
            {
                "score": hit.score,
                "page_number": hit.payload.get("page_number") if hit.payload else None,
                "reasons": hit.payload.get("reasons", []) if hit.payload else [],
            }
            for hit in (visual_results or [])
        ]

        dense_hits = getattr(text_result, "dense_hits", 0)
        sparse_hits = getattr(text_result, "sparse_hits", 0)

        logger.info(
            f"Retrieved {len(formatted_text_chunks)} text chunks "
            f"(Dense: {dense_hits}, Sparse: {sparse_hits}) "
            f"and {len(formatted_visual_pages)} visual pages."
        )

        return {
            "text_chunks": formatted_text_chunks,
            "visual_pages": formatted_visual_pages,
            "dense_hits": dense_hits,
            "sparse_hits": sparse_hits,
        }