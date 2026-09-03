"""
OCR Worker (Dedicated Visual Ingestion Pipeline)

Purpose:
- Handles resource-heavy image OCR tasks (scanned PDFs, JPEGs, PNGs).
- Isolated from standard text workers to prevent GPU/CPU starvation.
- Consumes from 'document.ocr.queue'.
"""
import uuid
import asyncio
import logging
import signal
from pathlib import Path

import aio_pika
import fitz  # PyMuPDF
from PIL import Image
from qdrant_client import AsyncQdrantClient, models
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.messaging.connection import rabbitmq_manager
from app.pipeline.detector.models import DocumentVisualJobMessage
from app.models.document import Document

from app.pipeline.embeddings.visual_engine import VisualRetrieverEngine
from app.utils.file_utils import ensure_upload_dir
from app.utils.logging_utils import configure_logging

configure_logging()
logger = logging.getLogger("visual_worker")

# no heavy loading on import
visual_engine = None
qdrant_client = None

# THE FIX: A stable namespace for generating deterministic UUIDs
QDRANT_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "privatedoc.rag")


def render_pdf_page_to_image(file_path: Path, page_number: int) -> Image.Image:
    """Renders a specific PDF page to a high-res PIL Image for the Vision Model."""
    try:
        doc = fitz.open(file_path)
        if page_number > len(doc):
            raise ValueError(f"Page {page_number} out of range for document with {len(doc)} pages.")
        
        page = doc[page_number - 1]
        matrix = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=matrix)

        mode = "RGBA" if pix.alpha else "RGB"
        img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)

        doc.close()
        return img
    except Exception as exc:
        logger.error(f"MuPDF rendering error on page {page_number} for {file_path.name}: {exc}")
        raise ValueError(f"Corrupted or unrenderable PDF page: {page_number}") from exc


async def process_visual_job(message: aio_pika.IncomingMessage) -> None:
    """Consumes visual processing tasks and generates multi-vector embeddings."""
    global visual_engine, qdrant_client

    # THE FIX: Removed async with message.process() to manually handle ACK/NACKs safely
    try:
        payload = DocumentVisualJobMessage.model_validate_json(message.body)
    except Exception as e:
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
        # Render the physical page to an image
        image = await asyncio.to_thread(
            render_pdf_page_to_image, file_path, payload.page_number
        )

        # Generate Late-Interaction Multi-Vectors
        multi_vector = await asyncio.to_thread(visual_engine.embed_image, image)

        point_string_id = f"{payload.document_id}_page_{payload.page_number}"
        
        # THE FIX: Deterministic UUID prevents Qdrant duplicate vectors if the job is rerun
        deterministic_uuid = str(uuid.uuid5(QDRANT_NAMESPACE, point_string_id))

        await qdrant_client.upsert(
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


async def run_worker() -> None:
    """Connects to RabbitMQ and starts the visual processing loop."""
    global visual_engine, qdrant_client

    logger.info("Starting Visual Representation Worker...")

    # Initialize Qdrant client first
    qdrant_client = AsyncQdrantClient(url=settings.qdrant_url)

    # Initialize heavy model safely inside the async loop thread
    logger.info("Loading ColQwen2 Vision Model into GPU...")
    visual_engine = await asyncio.to_thread(VisualRetrieverEngine)
    logger.info("Vision Model loaded successfully into GPU!")

    await rabbitmq_manager.initialize()
    channel = await rabbitmq_manager.create_consumer_channel()
    #ColPali takes VRAM/RAM. Process 1 visually-rich page at a time.
    await channel.set_qos(prefetch_count=1)

    # Note: Visual worker declares its queue directly here, no external helper needed
    queue = await channel.declare_queue("document.visual.queue", durable=True)

    # THE FIX: Graceful Shutdown event handles SIGTERM cleanly
    shutdown_event = asyncio.Event()

    def handle_shutdown(sig, frame):
        logger.warning(f"Received termination signal ({sig}). Initiating graceful shutdown...")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: handle_shutdown(s, None))

    logger.info(f"[*] Visual Worker actively listening on '{queue.name}'")
    consumer_tag = await queue.consume(process_visual_job)

    try:
        await shutdown_event.wait() 
    finally:
        logger.info("Graceful shutdown initiated. Stopping new message consumption...")
        await queue.cancel(consumer_tag)
        await channel.close()
        await rabbitmq_manager.close()
        if qdrant_client:
            await qdrant_client.close()
        logger.info("Visual Worker shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("Visual worker stopped manually.")