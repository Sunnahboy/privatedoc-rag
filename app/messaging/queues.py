import asyncio

from aio_pika.abc import AbstractQueue, AbstractRobustChannel

from app.config import settings

from .exchanges import declare_exchanges


async def setup_queues_and_bindings(
    channel: AbstractRobustChannel,
) -> dict[str, AbstractQueue]:
    """Sets up queues, dead-letters and binding keys."""

    exchanges = await declare_exchanges(channel)

    # 1 . Declare Dead Letter Queues(DLQ) concurrently 
    dlq_task = channel.declare_queue(queue=settings.DLQ_NAME, durable=True)

    # 2 Declare main processing Queues with DLX arguments
    queue_args = {
        "x-dead-letter-exchange": settings.DLX_EXCHANGE_NAME,
        "x-dead-letter-routing-key": settings.DLQ_ROUTING_KEY,
    }

    main_queue_task = await channel.declare_queue(
        queue=settings.INGESTION_QUEUE_NAME,
        durable=True,
        arguments=queue_args,
    )

    dlq, main_queue = await asyncio.gather(dlq_task, main_queue_task)

    # bind both queues to their respective exchange concurrently
    bind_dlq_task = dlq.bind(
        exchange=exchanges["dlx_exchange"], routing_key=settings.DLQ_ROUTING_KEY
    )
    bind_main_task = main_queue.bind(
        exchange=exchanges["doc_exchange"], routing_key=settings.INGESTION_ROUTING_KEY
    )

    await asyncio.gather(bind_dlq_task, bind_main_task)

    return {
        "main_queue": main_queue,
        "dlq": dlq,
    }
