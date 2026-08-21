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

# Mocked import: You will build this wrapper class to house the Transformers/PyTorch logic
from app.pipeline.embeddings.visual_engine import VisualRetrieverEngine
from app.utils.file_utils import ensure_upload_dir
from app.utils.logging_utils import configure_logging

configure_logging()
logger = logging.getLogger("visual_worker")

# no heavy loading on import
visual_engine = None
qdrant_client = None


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

    async with message.process(requeue=True):  # Auto-NACK on unhandled exceptions
        try:
            payload = DocumentVisualJobMessage.model_validate_json(message.body)

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
                    return

                upload_dir = ensure_upload_dir().resolve()
                file_path = (upload_dir / doc.stored_filename).resolve()

            if not file_path.exists():
                logger.error(f"File not found at resolved path: {file_path}. Dropping job.")
                return

            # Render the physical page to an image
            image = await asyncio.to_thread(
                render_pdf_page_to_image, file_path, payload.page_number
            )

            # Generate Late-Interaction Multi-Vectors
            multi_vector = await asyncio.to_thread(visual_engine.embed_image, image)

            point_id = f"{payload.document_id}_page_{payload.page_number}"

            await qdrant_client.upsert(
                collection_name="documents_visual",
                points=[
                    models.PointStruct(
                        id=str(uuid.uuid4()),
                        vector=multi_vector.tolist(),
                        payload={
                            "chunk_id": point_id,
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

        except Exception:
            logger.exception("Fatal error processing visual job: ")
            raise  # Triggers the re-queue or Dead Letter routing


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
    # CRITICAL: ColPali takes VRAM/RAM. Process 1 visually-rich page at a time.
    await channel.set_qos(prefetch_count=1)

    queue = await channel.declare_queue("document.visual.queue", durable=True)

    logger.info(f"[*] Visual Worker actively listening on '{queue.name}'")
    await queue.consume(process_visual_job)

    try:
        await asyncio.Future()  # Keeps worker process alive
    finally:
        await channel.close()
        await rabbitmq_manager.close()
        if qdrant_client:
            await qdrant_client.close()


if __name__ == "__main__":
    asyncio.run(run_worker())
