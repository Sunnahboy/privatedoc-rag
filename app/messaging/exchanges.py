import asyncio

import aio_pika
from aio_pika.abc import AbstractExchange, AbstractRobustChannel

from app.config import settings


async def declare_exchanges(
    channel: AbstractRobustChannel,
) -> dict[str, AbstractExchange]:
    """Declares all application exchanges."""

    # Schedule both exchange declarations simultaneously
    dlx_task = await channel.declare_exchange(
        name=settings.DLX_EXCHANGE_NAME,
        type=aio_pika.ExchangeType.DIRECT,
        durable=True,
    )

    doc_task = await channel.declare_exchange(
        name=settings.DOCUMENT_EXCHANGE_NAME,
        type=aio_pika.ExchangeType.DIRECT,
    )
    # await both network calls concurrently
    dlx_exchange, doc_exchange = await asyncio.gather(dlx_task, doc_task)

    return {
        "doc_exchange": doc_exchange,
        "dlx_exchange": dlx_exchange,
    }
