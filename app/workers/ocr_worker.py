"""
OCR Worker (Dedicated Visual Ingestion Pipeline)

Purpose:
- Handles resource-heavy image OCR tasks (scanned PDFs, JPEGs, PNGs).
- Isolated from standard text workers to prevent GPU/CPU starvation.
- Consumes from 'document.ocr.queue'.
"""

import asyncio
import logging

from app.utils.logging_utils import configure_logging

configure_logging()
logger = logging.getLogger("ocr_worker")


async def run_worker() -> None:
    """Placeholder for dedicated OCR background worker loop."""
    logger.info("OCR Worker is initialized (Placeholder).")
    logger.info("Waiting for tasks on 'document.ocr.queue'...")

    try:
        await asyncio.Future()  # Keeps worker process alive
    except KeyboardInterrupt:
        logger.info("Stopping OCR worker...")


if __name__ == "__main__":
    asyncio.run(run_worker())
