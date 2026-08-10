import asyncio

from aio_pika import IncomingMessage
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.messaging.connection import rabbitmq_manager
from app.messaging.messages import DocumentIngestMessage
from app.messaging.queues import setup_queues_and_bindings
from app.models.document import Document
from app.pipeline.ingestion.pipeline import IngestionPipeline
from app.utils.file_utils import ensure_upload_dir
from app.utils.logging_utils import logging

logger = logging.getLogger("ingestion_worker")


async def process_job(message: IncomingMessage) -> None:
    """Handles coming , state transitions, pipeline execution, and ACK/NACK rules."""
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
        if doc.status == "indexed":
            logger.info("Document %s is already indexed skipping", document_id)
            await message.ack()
            return
        stored_filename = doc.stored_filename
        doc.status = "processing"
        await db.commit()

        try:
            upload_dir = ensure_upload_dir()
            file_path = upload_dir / stored_filename

            pipeline = IngestionPipeline()
            try:
                ingestion_result = await pipeline.ingest(
                    document_id=doc.id,
                    file_path=file_path,
                )

                doc.status = "indexed"
                doc.total_chunks = ingestion_result.total_chunks
                doc.total_pages = ingestion_result.total_pages
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
                doc.status = "failed"
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
        # The ideal production approach: Safe, readable, and highly targeted
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


async def run_worker() -> None:
    """Starts the standalone worker looping using the RabbitMQ manager."""

    # Initialize the connection manager
    await rabbitmq_manager.initialize()

    # Get a dedicated consumer channel bypassing the publisher pool
    channel = await rabbitmq_manager.create_consumer_channel()

    # Prefetch=1 protects  memory constraints
    await channel.set_qos(prefetch_count=settings.prefetch_count)

    # Ensure Topology exists
    queues = await setup_queues_and_bindings(channel)

    main_queue = queues["main_queue"]

    logger.info("Ingestion Worker online. Listening on queue '%s'...", main_queue.name)

    await main_queue.consume(process_job)

    try:
        # Keeps worker process alive
        await asyncio.Future()
    finally:
        await channel.close()
        await rabbitmq_manager.close()


if __name__ == "__main__":
    asyncio.run(run_worker())
