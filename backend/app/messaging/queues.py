from aio_pika.abc import AbstractQueue, AbstractRobustChannel

from app.config import settings

from .exchanges import declare_exchanges


async def setup_queues_and_bindings(
    channel: AbstractRobustChannel,
) -> dict[str, AbstractQueue]:
    """Sets up queues, dead-letters and binding keys."""

    exchanges = await declare_exchanges(channel)

    # Declare the dead-letter queue and bind it to the DLX exchange.
    dlq = await channel.declare_queue(name=settings.DLQ_NAME, durable=True)
    await dlq.bind(
        exchange=exchanges["dlx_exchange"],
        routing_key=settings.DLQ_ROUTING_KEY,
    )

    # Declare the main processing queue with DLX arguments.
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
