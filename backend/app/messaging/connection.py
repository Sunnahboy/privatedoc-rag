import asyncio
import logging

import aio_pika
from aio_pika.abc import AbstractRobustChannel, AbstractRobustConnection
from aio_pika.pool import Pool

from app.config import settings

logger = logging.getLogger(__name__)


class RabbitMQManager:
    """
    Manages the application's RabbitMQ connection and channel lifecycle.

    Responsibilities:
    - Maintain one robust RabbitMQ connection per process.
    - Maintain a bounded channel pool.
    - Provide startup/shutdown lifecycle management.
    - Provide lightweight health checking.

    This class does NOT manage:
    - exchanges
    - queues
    - bindings
    - routing keys
    - application messages
    """

    def __init__(self) -> None:
        self._connection: AbstractRobustConnection | None = None
        self._channel_pool: Pool[AbstractRobustChannel] | None = None

        self._init_lock = asyncio.Lock()
        self._is_shutting_down = False

    # Connection

    async def _create_connection(self) -> AbstractRobustConnection:
        """Create the single robust RabbitMQ connection."""
        logger.info("Connecting to RabbitMQ...")

        connection = await aio_pika.connect_robust(
            settings.rabbitmq_url,
            timeout=settings.rabbitmq_connection_timeout,
        )

        connection.close_callbacks.add(self._on_connection_close)
        connection.reconnect_callbacks.add(self._on_connection_reconnect)

        logger.info("RabbitMQ connection established.")

        return connection

    # Channel pool

    async def _create_channel(self) -> AbstractRobustChannel:
        """Create a channel from the shared robust connection."""
        connection = self._connection

        if connection is None or connection.is_closed:
            raise RuntimeError("RabbitMQ connection is unavailable.")

        # RobustChannel participates in aio-pika's automatic recovery.
        channel = await connection.channel(
            on_return_raises=True,
        )

        return channel

    # Lifecycle

    async def initialize(self) -> None:
        """
        Initialize RabbitMQ exactly once.

        A connection is established immediately so startup failures
        are detected during application startup.
        """
        if self._channel_pool is not None:
            return

        async with self._init_lock:
            if self._channel_pool is not None:
                return

            if self._is_shutting_down:
                raise RuntimeError("Cannot initialize RabbitMQ during shutdown.")

            logger.info("Initializing RabbitMQ...")

            connection = await self._create_connection()

            pool = Pool(
                self._create_channel,
                max_size=settings.rabbitmq_channel_pool_size,
            )
            try:
                # Validate connection and channel readiness before setting state
                self._connection = connection
                async with pool.acquire() as channel:
                    await channel.ready()
                # commit state only after verification succeeds
                self._channel_pool = pool
            except Exception:
                logger.exception("Failed to initialize RabbitMQ channel pool.")
                # Clean up dandling connection/pool
                if pool:
                    await pool.close()
                if connection and not connection.is_closed():
                    await connection.close()
                self._connection = None
                self._channel_pool = None
                raise

            logger.info(
                "RabbitMQ initialized successfully (channels=%d).",
                settings.rabbitmq_channel_pool_size,
            )

    # Access

    def get_channel_pool(self) -> Pool[AbstractRobustChannel]:
        """
        Return the channel pool exclusively for short-lived operations (publishers).

        Important Note:
        - Use `async with pool.acquire() as channel:` to temporarily borrow a channel.
        - Do NOT use this pool for long-running consumers (`queue.consume`),
        as holding a pooled channel open indefinitely will permanently reduce
        the pool size and eventually lock out publishers.
        """
        if self._is_shutting_down:
            raise RuntimeError("RabbitMQ manager is shutting down.")

        pool = self._channel_pool

        if pool is None:
            raise RuntimeError("RabbitMQ manager has not been initialized.")

        return pool

    # Health

    async def create_consumer_channel(self) -> AbstractRobustChannel:
        """
        Create and return a dedicated, unpolled channel for long-running consumers.

        as:
        - Consumers must hold channels open indefinitely to listen to queues.
        - By creating a standalone channel directly from the connection, we prevent
          consumers from starving the publisher channel pool.
        """
        if self._is_shutting_down:
            raise RuntimeError("RabbitMQ manager is shutting down.")

        connection = self._connection
        if connection is None or connection.is_closed:
            raise RuntimeError("RabbitMQ connection is unavailable.")

        # Bypass the pool and spawn a dedicated channel directly from the connection
        return await connection.channel(on_return_raises=True)

    async def is_healthy(self) -> bool:
        """
        Verify that RabbitMQ has an active connection and that
        a channel can be acquired successfully.
        """
        if self._is_shutting_down or not self._connection or not self._channel_pool:
            return False

        if self._connection.is_closed:
            return False
        # Degrading to unhealthy if pool is full protects upstream callers from timing out
        if self._channel_pool.size >= self._channel_pool.max:
            logger.warning("RabbitMQ channel pool is completely full.")
            return False

        return True

    # Shutdown

    async def publish_to_graveyard(self, body: bytes) -> None:
        """Publish a message directly to the DLQ exchange for dead-letter routing."""
        if self._is_shutting_down:
            raise RuntimeError("RabbitMQ manager is shutting down.")

        pool = self._channel_pool
        if pool is None:
            raise RuntimeError("RabbitMQ manager has not been initialized.")

        async with pool.acquire() as channel:
            exchange = await channel.get_exchange(
                settings.DLX_EXCHANGE_NAME, ensure=True
            )
            await exchange.publish(
                aio_pika.Message(
                    body=body,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    content_type="application/json",
                ),
                routing_key=settings.DLQ_ROUTING_KEY,
            )

    async def close(self) -> None:
        """Gracefully close RabbitMQ resources."""
        async with self._init_lock:
            if self._is_shutting_down:
                return

            self._is_shutting_down = True

            logger.info("Closing RabbitMQ...")

            # Stop new channel acquisition first.
            if self._channel_pool is not None:
                await self._channel_pool.close()
                self._channel_pool = None

            # Then close the underlying robust connection.
            if self._connection is not None:
                await self._connection.close()
                self._connection = None

            logger.info("RabbitMQ closed successfully.")

    # Observability

    @staticmethod
    def _on_connection_close(
        sender: AbstractRobustConnection,
        exc: BaseException | None,
    ) -> None:
        if exc:
            logger.warning(
                "RabbitMQ connection closed unexpectedly: %s",
                exc,
            )
        else:
            logger.info("RabbitMQ connection closed cleanly.")

    @staticmethod
    def _on_connection_reconnect(sender: AbstractRobustConnection) -> None:
        logger.info("RabbitMQ connection re-established.")


# One manager per application process.
rabbitmq_manager = RabbitMQManager()
