import logging

import aio_pika

from app.config import settings

from .connection import rabbitmq_manager
from .messages import DocumentIngestMessage, ChatGenerationMessage

logger = logging.getLogger(__name__)


async def publish_ingestion_job(document_id: str, storage_key: str) -> None:
    """Publishes a persistent document ingestion job using a pooled channel."""
    pool = rabbitmq_manager.get_channel_pool()

    payload = DocumentIngestMessage(
        document_id=document_id,
        storage_key=storage_key,
    )

    message = aio_pika.Message(
        body=payload.model_dump_json().encode("utf-8"),
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        content_type="application/json",
    )

    async with pool.acquire() as channel:
        exchange = await channel.declare_exchange(
            name=settings.DOCUMENT_EXCHANGE_NAME, 
            type=aio_pika.ExchangeType.DIRECT,
            ensure=True
        )
        await exchange.publish(message, routing_key=settings.INGESTION_ROUTING_KEY)

    logger.info("Publish ingestion job for document: %s", document_id)

async def publish_chat_job(
    message_id: str, 
    session_id: str, 
    question: str, 
    document_id: str | None
)->None:
    """Publishe a persitent chat message using a pooled channel"""
    pool = rabbitmq_manager.get_channel_pool()
    
    #trict validation via Pydantic
    payload = ChatGenerationMessage(
        message_id=message_id,
        session_id=session_id,
        question=question,
        document_id=document_id,
    )

    #Package as a persistent message
    message = aio_pika.Message(
        body=payload.model_dump_json().encode("utf-8"),
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        content_type="application/json",
    )

    #Publish using the connection pool
    async with pool.acquire() as channel:
        exchange = await channel.declare_exchange(
            name=settings.CHAT_EXCHANGE_NAME,
            type=aio_pika.ExchangeType.DIRECT,
            durable=True
        )
        logger.warning(f"!!! PUBLISHING TO EXCHANGE: '{settings.CHAT_EXCHANGE_NAME}' WITH KEY: '{settings.CHAT_ROUTING_KEY}' !!!")
        await exchange.publish(message, routing_key=settings.CHAT_ROUTING_KEY)

    logger.info("Published chat generation job for message: %s", message_id)
