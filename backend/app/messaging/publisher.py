import logging

import aio_pika

from app.config import settings

from .connection import rabbitmq_manager
from .messages import DocumentIngestMessage

logger = logging.getLogger(__name__)


async def publish_ingestion_job(document_id: str, storage_key: str) -> None:
    """Publishes a persistent document ingestion job using a pooled channel."""
    # get the channel
    pool = rabbitmq_manager.get_channel_pool()

    # acquire a channel temporarily
    async with pool.acquire() as channel:
        # get the exchange
        exchange = await channel.get_exchange(
            settings.DOCUMENT_EXCHANGE_NAME, ensure=True
        )

    payload = DocumentIngestMessage(
        document_id=document_id,
        storage_key=storage_key,
    )

    message = aio_pika.Message(
        body=payload.model_dump_json().encode("utf-8"),
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        content_type="application/json",
    )

    await exchange.publish(message, routing_key=settings.INGESTION_ROUTING_KEY)
    logger.info("Publish ingestion job for document: %s", document_id)
