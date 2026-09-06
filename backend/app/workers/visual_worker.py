"""
OCR Worker (Dedicated Visual Ingestion Pipeline)

Purpose:
- Handles resource-heavy image OCR tasks (scanned PDFs, JPEGs, PNGs).
- Uses a centralized Model-as-a-Service (MaaS) API to offload VRAM pressure.
- Consumes from 'document.visual.queue'.
"""

import asyncio
import logging
import signal
import uuid
from pathlib import Path

import aio_pika
import fitz  # PyMuPDF
from PIL import Image
from qdrant_client import AsyncQdrantClient, models
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.messaging.connection import rabbitmq_manager
from app.models.document import Document
from app.pipeline.detector.models import DocumentVisualJobMessage

# Lightweight HTTP client instead of heavy PyTorch model
from app.pipeline.embeddings.visual_client import VisualAPIClient
from app.utils.file_utils import ensure_upload_dir
from app.utils.logging_utils import configure_logging

configure_logging()
logger = logging.getLogger("visual_worker")

# A stable namespace for generating deterministic UUIDs
QDRANT_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "privatedoc.rag")


def render_pdf_page_to_image(file_path: Path, page_number: int) -> Image.Image:
    """Renders a specific PDF page to a high-res PIL Image for the Vision API."""
    try:
        doc = fitz.open(file_path)
        if page_number > len(doc):
            raise ValueError(
                f"Page {page_number} out of range for document with {len(doc)} pages."
            )

        page = doc[page_number - 1]
        matrix = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=matrix)

        mode = "RGBA" if pix.alpha else "RGB"
        img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)

        doc.close()
        return img
    except Exception as exc:
        logger.error(
            f"MuPDF rendering error on page {page_number} for {file_path.name}: {exc}"
        )
        raise ValueError(f"Corrupted or unrenderable PDF page: {page_number}") from exc


class VisualWorker:
    """
    OOP Encapsulation of the Visual Worker.
    Eliminates fragile global variables and properly manages connection state.
    """

    def __init__(self):
        # State explicitly tied to the instance
        self.qdrant_client: AsyncQdrantClient | None = None
        self.visual_engine: VisualAPIClient | None = None
        self.channel: aio_pika.RobustChannel | None = None

    async def process_job(self, message: aio_pika.IncomingMessage) -> None:
        """Consumes visual processing tasks and routes them to the centralized API."""
        try:
            payload = DocumentVisualJobMessage.model_validate_json(message.body)
        except Exception as e:#noqa
            logger.critical(f"Invalid visual message payload dropped: {e}")
            await message.reject(requeue=False)
            return

        logger.info(
            f"Processing Visual Page | Doc: {payload.document_id} | "
            f"Page: {payload.page_number} | Trigger: {payload.classification}"
        )

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Document).where(Document.id == payload.document_id)
            )
            doc = result.scalars().first()
            if not doc or not doc.stored_filename:
                logger.error(
                    f"Document {payload.document_id} not found in DB. Dropping job."
                )
                await message.reject(requeue=False)
                return

            upload_dir = ensure_upload_dir().resolve()
            file_path = (upload_dir / doc.stored_filename).resolve()

        if not file_path.exists():
            logger.error(f"File not found at resolved path: {file_path}. Dropping job.")
            await message.reject(requeue=False)
            return

        try:
            # CPU-bound rendering safely offloaded
            image = await asyncio.to_thread(
                render_pdf_page_to_image, file_path, payload.page_number
            )

            # Generate Late-Interaction Multi-Vectors via HTTP Bridge
            multi_vector = await self.visual_engine.embed_image(image)

            point_string_id = f"{payload.document_id}_page_{payload.page_number}"

            # Deterministic UUID prevents Qdrant duplicate vectors if the job is rerun
            deterministic_uuid = str(uuid.uuid5(QDRANT_NAMESPACE, point_string_id))

            await self.qdrant_client.upsert(
                collection_name="documents_visual",
                points=[
                    models.PointStruct(
                        id=deterministic_uuid,
                        vector=multi_vector.tolist(),
                        payload={
                            "chunk_id": point_string_id,
                            "document_id": payload.document_id,
                            "page_number": payload.page_number,
                            "classification": payload.classification,
                            "reasons": payload.reasons,
                        },
                    )
                ],
            )

            logger.info(
                f"Successfully visually indexed page {payload.page_number} "
                f"for doc {payload.document_id}"
            )
            await message.ack()

        except Exception:
            logger.exception("Recoverable error processing visual job, requeuing: ")
            await message.reject(requeue=True)

    async def run(self) -> None:
        """Initializes dependencies and enters the RabbitMQ consumer loop."""
        logger.info("Starting Visual Representation Worker...")

        # Initialize clients natively within the class instance
        self.qdrant_client = AsyncQdrantClient(url=settings.qdrant_url)

        logger.info("Initializing connection to Centralized Visual API...")
        self.visual_engine = VisualAPIClient()

        await rabbitmq_manager.initialize()
        self.channel = await rabbitmq_manager.create_consumer_channel()

        # Process 1 page at a time to prevent flooding the microservice lock
        await self.channel.set_qos(prefetch_count=1)

        queue = await self.channel.declare_queue("document.visual.queue", durable=True)

        # OS Signal handling for graceful shutdown
        shutdown_event = asyncio.Event()

        def handle_shutdown(sig, frame):
            logger.warning(
                f"Received termination signal ({sig}). Initiating graceful shutdown..."
            )
            shutdown_event.set()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: handle_shutdown(s, None))

        logger.info(f"[*] Visual Worker actively listening on '{queue.name}'")

        # RabbitMQ strictly passes `message`, so we pass the bound method
        consumer_tag = await queue.consume(self.process_job)

        try:
            await shutdown_event.wait()
        finally:
            logger.info(
                "Graceful shutdown initiated. Stopping new message consumption..."
            )
            await queue.cancel(consumer_tag)

            # Clean closure of all network socket pools
            if self.channel:
                await self.channel.close()

            await rabbitmq_manager.close()

            if self.qdrant_client:
                await self.qdrant_client.close()

            if self.visual_engine:
                await self.visual_engine.close()

            logger.info("Visual Worker shutdown complete.")


if __name__ == "__main__":
    try:
        # Instantiate the isolated class and run
        worker = VisualWorker()
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        logger.info("Visual worker stopped manually via KeyboardInterrupt.")
