"""
OCR Worker (Dedicated Visual Ingestion Pipeline)

Purpose:
- Handles resource-heavy image OCR tasks (scanned PDFs, JPEGs, PNGs).
- Isolated from standard text workers to prevent GPU/CPU starvation.
- Consumes from 'document.ocr.queue'.
"""

import asyncio
import logging
from pathlib import Path

import aio_pika
import fitz  # PyMuPDF
from PIL import Image
from qdrant_client import AsyncQdrantClient, models

from app.config import settings
from app.messaging.connection import rabbitmq_manager
from app.pipeline.detector.models import DocumentVisualJobMessage

# Mocked import: You will build this wrapper class to house the Transformers/PyTorch logic
from app.pipeline.embeddings.visual_engine import VisualRetrieverEngine
from app.utils.logging_utils import configure_logging

configure_logging()
logger = logging.getLogger("visual_worker")

# Initialize Heavy Models Globally
visual_engine = VisualRetrieverEngine()
qdrant_client = AsyncQdrantClient(url=settings.qdrant_url)


def render_pdf_page_to_image(file_path: Path, page_number: int) -> Image.Image:
    """Renders a specific PDF page to a high-res PIL Image for the Vision Model."""
    doc = fitz.open(file_path)
    # PyMuPDF is 0-indexed, our detector emits 1-indexed page numbers
    page = doc[page_number - 1]

    # Render at 2x scale (144 DPI) for crisp image patches
    matrix = fitz.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=matrix)

    # Convert PyMuPDF Pixmap to PIL Image (required by ColPali/Transformers)
    mode = "RGBA" if pix.alpha else "RGB"
    img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)

    doc.close()
    return img


async def process_visual_job(message: aio_pika.IncomingMessage) -> None:
    """Consumes visual processing tasks and generates multi-vector embeddings."""
    async with message.process(requeue=True):  # Auto-NACK on unhandled exceptions
        try:
            payload = DocumentVisualJobMessage.model_validate_json(message.body)

            logger.info(
                f"Processing Visual Page | Doc: {payload.document_id} | "
                f"Page: {payload.page_number} | Trigger: {payload.classification}"
            )

            file_path = Path(settings.upload_dir) / f"{payload.document_id}.pdf"
            if not file_path.exists():
                logger.error(f"File not found: {file_path}. Dropping job.")
                return

            # 1. Render the physical page to an image
            # Run blocking CPU task in a thread
            image = await asyncio.to_thread(
                render_pdf_page_to_image, file_path, payload.page_number
            )

            # 2. Generate Late-Interaction Multi-Vectors (Heavy GPU/CPU Math)
            # Returns a 2D numpy array/tensor: shape (num_patches, vector_dim)
            multi_vector = await asyncio.to_thread(visual_engine.embed_image, image)

            # 3. Upsert to Qdrant using the Multi-Vector payload format
            point_id = f"{payload.document_id}_page_{payload.page_number}"

            await qdrant_client.upsert(
                collection_name="documents_visual",
                points=[
                    models.PointStruct(
                        id=point_id,  # Ensure you use a valid UUID hash in production
                        vector=multi_vector.tolist(),  # Convert numpy array to list of lists
                        payload={
                            "document_id": payload.document_id,
                            "page_number": payload.page_number,
                            "classification": payload.classification,
                            "reasons": payload.reasons,
                        },
                    )
                ],
            )

            logger.info(f"Successfully visually indexed page {payload.page_number}")

        except Exception:
            logger.exception("Fatal error processing visual job: ")
            raise  # Triggers the re-queue or Dead Letter routing


async def run_worker() -> None:
    """Connects to RabbitMQ and starts the visual processing loop."""
    logger.info("Starting Visual Representation Worker...")

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


if __name__ == "__main__":
    asyncio.run(run_worker())
