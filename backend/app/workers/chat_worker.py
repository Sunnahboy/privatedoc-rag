import asyncio
import logging
import signal

import httpx
from aio_pika import IncomingMessage
from qdrant_client import AsyncQdrantClient

from app.config import settings
from app.database import AsyncSessionLocal
from app.messaging.connection import rabbitmq_manager
from app.messaging.messages import ChatGenerationMessage
from app.messaging.queues import setup_queues_and_bindings
from app.orchestration.rag_pipeline import RAGPipeline
from app.pipeline.embeddings.fastembed_embedder import FastEmbedEmbedder
from app.pipeline.embeddings.visual_client import VisualAPIClient
from app.pipeline.retrieval.bm25_retriever import BM25Retriever
from app.pipeline.retrieval.hybrid_retriever import HybridRetriever
from app.pipeline.retrieval.multimodal_pipeline import MultimodalRetrievalPipeline
from app.pipeline.retrieval.multimodal_retriever import MultimodalRetriever
from app.pipeline.retrieval.qdrant_retriever import QdrantRetriever
from app.pipeline.retrieval.query_rewriter import QueryRewriter
from app.pipeline.retrieval.query_router import HybridQueryRouter
from app.utils.logging_utils import configure_logging

from .Chatworker import ChatWorker as CoreChatWorker  # Aliased to avoid naming conflict

configure_logging()
logger = logging.getLogger(__name__)


class ChatGenerationService:
    """

    Owns its dependencies natively to prevent scope leaks and nested closures.
    """

    def __init__(self):
        self.qdrant_client: AsyncQdrantClient | None = None
        self.visual_engine: VisualAPIClient | None = None
        self.rag_pipeline: RAGPipeline | None = None
        self.query_rewriter: QueryRewriter | None = None
        self.query_router: HybridQueryRouter | None = None
        self.channel = None

    async def process_job(self, message: IncomingMessage) -> None:
        """RabbitMQ Callback."""
        try:
            payload = ChatGenerationMessage.model_validate_json(message.body)
        except Exception as e:  # noqa
            logger.critical("Invalid chat message payload dropped: %s", e)
            await message.reject(requeue=False)
            return

        should_reject = False

        async with AsyncSessionLocal() as db:
            # Instantiate the business logic handler using self-owned dependencies
            worker = CoreChatWorker(
                rag_pipeline=self.rag_pipeline,
                query_rewriter=self.query_rewriter,
                query_router=self.query_router,
            )

            try:
                logger.info(f"Processing chat job for message {payload.message_id}")
                await worker.process_chat_job(
                    message_id=payload.message_id,
                    session_id=payload.session_id,
                    question=payload.question,
                    document_ids=payload.document_ids,
                    db=db,
                )
                await message.ack()
                logger.info(f"Successfully finished chat job for {payload.message_id}")

            except Exception as exc:  # noqa
                logger.error(
                    "Chat generation failed for %s: %s", payload.message_id, exc
                )
                should_reject = True

        # Handle retries completely outside of the DB transaction block
        if should_reject:
            headers = message.headers or {}
            x_death = headers.get("x-death", [])
            retry_count = next(
                (
                    entry.get("count", 0)
                    for entry in (x_death or [])
                    if entry.get("queue") == settings.CHAT_QUEUE_NAME
                ),
                0,
            )

            if retry_count < settings.MAX_RETRIES:
                logger.warning(
                    "Rejecting chat job %s for retry (Attempt %d/%d)",
                    payload.message_id,
                    retry_count + 1,
                    settings.MAX_RETRIES,
                )
                await message.reject(requeue=False)
            else:
                logger.critical(
                    "Max retries exceeded for chat job %s. Routing to graveyard.",
                    payload.message_id,
                )
                await message.ack()
                await rabbitmq_manager.publish_to_graveyard(message.body)

    async def run(self) -> None:
        """Initializes infrastructure and enters the consumption loop."""
        logger.info("Starting Chat Generation Worker...")
        await rabbitmq_manager.initialize()

        logger.info("Loading AI models and RAG pipeline into memory...")
        self.qdrant_client = AsyncQdrantClient(url=settings.qdrant_url)
        base_retriever = HybridRetriever(
            dense=QdrantRetriever(), sparse=BM25Retriever()
        )
        logger.info("Initializing global HTTP client...")
        self.http_client = httpx.AsyncClient(timeout=60.0)

        # Inject the single client into the rewriter (Option A)
        self.query_rewriter = QueryRewriter(client=self.http_client)

        logger.info("Connecting to Centralized Visual API...")
        self.visual_engine = VisualAPIClient()

        multi_retriever = MultimodalRetriever(
            qdrant_client=self.qdrant_client,
            text_retriever=base_retriever,
            visual_engine=self.visual_engine,
        )
        multimodal_pipeline = MultimodalRetrievalPipeline(retriever=multi_retriever)

        self.rag_pipeline = RAGPipeline(
            retriever=base_retriever, multimodal_pipeline=multimodal_pipeline
        )
        
        # Instantiate the Embedder and Router, then pre-compute anchors
        logger.info("Initializing Hybrid Query Router...")
        text_embedder = FastEmbedEmbedder()
        self.query_router = HybridQueryRouter(embedder=text_embedder)
        await self.query_router.initialize()

        logger.info("AI Pipeline loaded successfully.")

        self.channel = await rabbitmq_manager.create_consumer_channel()
        await self.channel.set_qos(prefetch_count=settings.prefetch_count)

        queues = await setup_queues_and_bindings(self.channel)
        chat_queue = queues["chat_queue"]

        shutdown_event = asyncio.Event()

        def handle_shutdown(sig, frame):
            logger.warning(
                f"Received termination signal ({sig}). Initiating graceful shutdown..."
            )
            shutdown_event.set()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: handle_shutdown(s, None))

        logger.info("Chat Worker online. Listening on queue '%s'...", chat_queue.name)

        # Pass the bound method directly to the consumer
        consumer_tag = await chat_queue.consume(self.process_job)

        try:
            await shutdown_event.wait()
        finally:
            logger.info(
                "Graceful shutdown initiated. Stopping new message consumption..."
            )
            try:
                await asyncio.wait_for(chat_queue.cancel(consumer_tag), timeout=2.0) 
            except Exception as e:#noqa
                logger.warning(f"Could not cleanly cancel consumer (broker likely down): {e}")

            if self.http_client:
                try:
                    await asyncio.wait_for(self.http_client.aclose(), timeout=2.0)
                except Exception as e:  # noqa
                    logger.warning(f"Failed to close HTTP client: {e}")
            if self.rag_pipeline:
                await self.rag_pipeline.close()
            if self.qdrant_client:
                await self.qdrant_client.close()
            if self.visual_engine:
                await self.visual_engine.close()

            if self.channel:
                await self.channel.close()
            await rabbitmq_manager.close()

            logger.info("Chat Worker shutdown complete.")


if __name__ == "__main__":
    try:
        service = ChatGenerationService()
        asyncio.run(service.run())
    except KeyboardInterrupt:
        logger.info("Chat Worker stopped manually.")
