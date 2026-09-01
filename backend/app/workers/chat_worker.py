import asyncio
import logging
from aio_pika import IncomingMessage

from app.config import settings
from app.database import AsyncSessionLocal
from app.messaging.connection import rabbitmq_manager
from app.messaging.messages import ChatGenerationMessage
from app.messaging.queues import setup_queues_and_bindings
from app.pipeline.retrieval.hybrid_retriever import HybridRetriever
from app.pipeline.retrieval.bm25_retriever import BM25Retriever
from app.pipeline.retrieval.qdrant_retriever import QdrantRetriever
from app.pipeline.embeddings.visual_engine import VisualRetrieverEngine
from qdrant_client import AsyncQdrantClient
from app.pipeline.retrieval.multimodal_retriever import MultimodalRetriever
from app.pipeline.retrieval.multimodal_pipeline import MultimodalRetrievalPipeline
from app.orchestration.rag_pipeline import RAGPipeline
from app.utils.logging_utils import configure_logging

# WHAT BREAKS: If you are on Windows/Mac, this import might fail due to case-insensitivity.
from .Chatworker import ChatWorker

configure_logging()
logger = logging.getLogger(__name__)

async def process_message(message: IncomingMessage, rag_pipeline: RAGPipeline) -> None:
    try:
        payload = ChatGenerationMessage.model_validate_json(message.body)
    except Exception as e:
        logger.critical("Invalid chat message payload dropped: %s", e)
        await message.reject(requeue=False)
        return

    should_reject = False
    async with AsyncSessionLocal() as db:
        worker = ChatWorker(rag_pipeline=rag_pipeline)
        try:
            logger.info(f"Processing chat job for message {payload.message_id}")
            await worker.process_chat_job(
                message_id=payload.message_id,
                session_id=payload.session_id,
                question=payload.question,
                document_id=payload.document_id,
                db=db
            )
            await message.ack()
            logger.info(f"Successfully finished chat job for {payload.message_id}")
        except Exception as exc:
            logger.error("Chat generation failed for %s: %s", payload.message_id, exc)
            should_reject = True

    if should_reject:
        headers = message.headers or {}
        x_death = headers.get("x-death", [])
        retry_count = next(
            (entry.get("count", 0) for entry in (x_death or []) if entry.get("queue") == settings.CHAT_QUEUE_NAME),
            0,
        )

        if retry_count < settings.MAX_RETRIES:
            logger.warning(
                "Rejecting chat job %s for retry (Attempt %d/%d)",
                payload.message_id, retry_count + 1, settings.MAX_RETRIES
            )
            await message.reject(requeue=False)
        else:
            logger.critical("Max retries exceeded for chat job %s. Routing to graveyard.", payload.message_id)
            await message.ack()
            await rabbitmq_manager.publish_to_graveyard(message.body)

async def run_worker() -> None:
    logger.info("Starting Chat Generation Worker...")
    await rabbitmq_manager.initialize()

    logger.info("Loading AI models and RAG pipeline into memory...")
    qdrant_client = AsyncQdrantClient(url=settings.qdrant_url)
    base_retriever = HybridRetriever(dense=QdrantRetriever(), sparse=BM25Retriever())
    visual_engine = VisualRetrieverEngine()
    
    multi_retriever = MultimodalRetriever(
        qdrant_client=qdrant_client,
        text_retriever=base_retriever,
        visual_engine=visual_engine
    )
    multimodal_pipeline = MultimodalRetrievalPipeline(retriever=multi_retriever)
    
    rag_pipeline = RAGPipeline(
        retriever=base_retriever,
        multimodal_pipeline=multimodal_pipeline
    )
    logger.info("AI Pipeline loaded successfully.")

    channel = await rabbitmq_manager.create_consumer_channel()
    await channel.set_qos(prefetch_count=settings.prefetch_count)

    queues = await setup_queues_and_bindings(channel)
    chat_queue = queues["chat_queue"] 

    logger.info("Chat Worker online. Listening on queue '%s'...", chat_queue.name)

    await chat_queue.consume(
        lambda msg: process_message(msg, rag_pipeline)
    )

    try:
        await asyncio.Future()
    finally:
        await rag_pipeline.close()
        await channel.close()
        await rabbitmq_manager.close()

if __name__ == "__main__":
    asyncio.run(run_worker())