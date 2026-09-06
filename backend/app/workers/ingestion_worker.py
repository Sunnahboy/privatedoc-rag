import asyncio
import logging
import signal
from aio_pika import IncomingMessage
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.messaging.connection import rabbitmq_manager
from app.messaging.messages import DocumentIngestMessage
from app.messaging.queues import setup_queues_and_bindings
from app.models.document import Document, IngestStatus
from app.pipeline.ingestion.pipeline import IngestionPipeline
from app.utils.file_utils import ensure_upload_dir
from app.utils.logging_utils import configure_logging

configure_logging()
logger = logging.getLogger(__name__)


class DocumentIngestionService:
    """
    OOP Encapsulation of the Document Ingestion Worker.
    Ensures safe state management and graceful shutdowns during heavy CPU/IO loads.
    """
    def __init__(self):
        self.channel = None

    async def process_job(self, message: IncomingMessage) -> None:
        """Handles incoming messages, state transitions, pipeline execution, and ACK/NACK rules."""
        try:
            payload = DocumentIngestMessage.model_validate_json(message.body)
            document_id = payload.document_id
        except Exception as e:  # noqa
            logger.critical("Invalid message payload dropped: %s", e)
            # Reject immediately without requeue so it hits the DLQ, and stop processing.
            await message.reject(requeue=False)
            return

        # Track execution status
        should_reject = False

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Document).where(Document.id == document_id))
            doc = result.scalars().first()

            if not doc:
                logger.error("Document %s not found in DB. Dropping job.", document_id)
                await message.ack()  # removed invalid jobs
                return
            if doc.status == IngestStatus.COMPLETED:
                logger.info("Document %s is already indexed skipping", document_id)
                await message.ack()
                return
            
            stored_filename = doc.stored_filename
            doc.status = IngestStatus.PROCESSING_TEXT
            await db.commit()

            try:
                upload_dir = ensure_upload_dir()
                file_path = upload_dir / stored_filename

                # Instantiate pipeline per-document to isolate extraction state
                pipeline = IngestionPipeline()
                try:
                    ingestion_result = await pipeline.ingest(
                        document_id=doc.id,
                        file_path=file_path,
                    )

                    doc.status = IngestStatus.COMPLETED
                    doc.total_chunks = ingestion_result.total_chunks
                    doc.total_pages = ingestion_result.total_pages
                    doc.toc = ingestion_result.toc

                    await db.commit()
                    logger.info("Successfully indexed document %s", document_id)
                    await message.ack()  # manually ack successful run
                finally:
                    await pipeline.close()

            except Exception as exc:  # noqa
                await db.rollback()
                logger.error(
                    "Processing pipeline failed for document %s: %s", document_id, exc
                )
                try:
                    doc.status = IngestStatus.FAILED
                    await db.commit()
                except Exception as db_exc:  # noqa
                    logger.critical(
                        "Secondary DB error updating failure status for %s: %s",
                        document_id,
                        db_exc,
                    )

                should_reject = True

        # Handle RabbitMQ routing completely outside of the database transactional scope
        if should_reject:
            headers = message.headers or {}
            x_death = headers.get("x-death", [])
            retry_count = next(
                (
                    entry.get("count", 0)
                    for entry in (x_death or [])
                    if entry.get("queue") == "document.ingest.queue"
                ),
                0,
            )

            if retry_count < settings.MAX_RETRIES:
                logger.warning(
                    "Rejecting document %s for retry (Attempt %d/%d)",
                    document_id,
                    retry_count + 1,
                    settings.MAX_RETRIES,
                )
                await message.reject(requeue=False)  # Routes to DLX for retry

            else:
                logger.critical(
                    "Max retries exceeded for document %s. routing to DQ.",
                    document_id,
                )
                await message.ack()
                await rabbitmq_manager.publish_to_graveyard(message.body)


    async def run(self) -> None:
        """Starts the standalone worker looping using the RabbitMQ manager."""
        logger.info("Starting ingestion worker...")
        
        await rabbitmq_manager.initialize()
        self.channel = await rabbitmq_manager.create_consumer_channel()
        await self.channel.set_qos(prefetch_count=settings.prefetch_count)
        
        queues = await setup_queues_and_bindings(self.channel)
        main_queue = queues["main_queue"]

        shutdown_event = asyncio.Event()

        # Define the signal handler
        def handle_shutdown(sig, frame):
            logger.warning(f"Received termination signal ({sig}). Initiating graceful shutdown...")
            shutdown_event.set()

        # Register the signal handlers (Ctrl+C and Docker SIGTERM)
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: handle_shutdown(s, None))

        logger.info("Ingestion Worker online. Listening on queue '%s'...", main_queue.name)

        # Start consuming messages using the bound class method
        consumer_tag = await main_queue.consume(self.process_job)

        try:
            # Wait until a shutdown signal is received
            await shutdown_event.wait()
        finally:
            logger.info("Graceful shutdown initiated. Stopping new message consumption...")
            # 1. Stop taking new jobs immediately
            await main_queue.cancel(consumer_tag)
            
            # 2. Close channels and connections cleanly
            logger.info("Closing RabbitMQ connections...")
            if self.channel:
                await self.channel.close()
            await rabbitmq_manager.close()
            
            logger.info("Worker shutdown complete.")


if __name__ == "__main__":
    try:
        service = DocumentIngestionService()
        asyncio.run(service.run())
    except KeyboardInterrupt:
        # Fallback for manual Ctrl+C in terminals that might bypass the signal handler
        logger.info("Worker stopped manually.")