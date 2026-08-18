import asyncio
import logging
from typing import Any

from app.pipeline.embeddings.base import BaseEmbedder
from app.pipeline.embeddings.visual_engine import VisualRetrieverEngine
from qdrant_client import AsyncQdrantClient, models

logger = logging.getLogger(__name__)


class MultimodalRetriever:
    def __init__(
        self,
        qdrant_client: AsyncQdrantClient,
        text_embedder: BaseEmbedder,
        visual_engine: VisualRetrieverEngine,
    ):
        self.client = qdrant_client
        self.text_embedder = text_embedder
        self.visual_engine = visual_engine

        self.text_collection = "documents_text"
        self.visual_collection = "documents_visual"

    async def retrieve(
        self, query: str, document_id: str, limit: int = 5
    ) -> dict[str, list[Any]]:
        """
        Executes parallel searches across both the text and visual collections.
        Filters by the specific document_id.
        """
        logger.info(f"Executing multimodal retrieval for query: '{query}'")

        # 1. Generate Embeddings (CPU/GPU bound, run in threads to avoid blocking)
        text_vector_task = asyncio.to_thread(self.text_embedder.embed_query, query)
        visual_vector_task = asyncio.to_thread(self.visual_engine.embed_query, query)

        text_vector, visual_vector = await asyncio.gather(
            text_vector_task, visual_vector_task
        )

        # 2. Setup the Document Filter
        doc_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="document_id", match=models.MatchValue(value=document_id)
                )
            ]
        )

        # 3. Execute Qdrant Searches Concurrently
        text_search_task = self.client.search(
            collection_name=self.text_collection,
            query_vector=text_vector,
            query_filter=doc_filter,
            limit=limit,
        )

        visual_search_task = self.client.search(
            collection_name=self.visual_collection,
            # CRITICAL: We must format the ColPali query as a MultiVector
            query_vector=models.MultiVectorQuery(multi_vector=visual_vector.tolist()),
            query_filter=doc_filter,
            limit=limit,
        )

        text_results, visual_results = await asyncio.gather(
            text_search_task, visual_search_task
        )

        # 4. Format and Return Results
        formatted_results = {
            "text_chunks": [
                {
                    "score": hit.score,
                    "text": hit.payload.get("text", ""),
                    "page_number": hit.payload.get("page_number"),
                }
                for hit in text_results
            ],
            "visual_pages": [
                {
                    "score": hit.score,
                    "page_number": hit.payload.get("page_number"),
                    "reasons": hit.payload.get("reasons", []),
                }
                for hit in visual_results
            ],
        }

        logger.info(
            f"Retrieved {len(formatted_results['text_chunks'])} text chunks and "
            f"{len(formatted_results['visual_pages'])} visual pages."
        )

        return formatted_results
