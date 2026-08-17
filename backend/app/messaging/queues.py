from aio_pika.abc import AbstractQueue, AbstractRobustChannel

from app.config import settings

from .exchanges import declare_exchanges


async def setup_queues_and_bindings(
    channel: AbstractRobustChannel,
) -> dict[str, AbstractQueue]:
    """Sets up queues, dead-letters and binding keys."""

    exchanges = await declare_exchanges(channel)

    # Declare Dead Letter Queues(DLQ) concurrently
    dlq = channel.declare_queue(name=settings.DLQ_NAME, durable=True)

    # Declare main processing Queues with DLX arguments
    queue_args = {
        "x-dead-letter-exchange": settings.DLX_EXCHANGE_NAME,
        "x-dead-letter-routing-key": settings.DLQ_ROUTING_KEY,
    }

    main_queue = await channel.declare_queue(
        name=settings.INGESTION_QUEUE_NAME,
        durable=True,
        arguments=queue_args,
    )

    await main_queue.bind(
        exchange=exchanges["doc_exchange"], routing_key=settings.INGESTION_ROUTING_KEY
    )

    return {
        "main_queue": main_queue,
        "dlq": dlq,
    }
