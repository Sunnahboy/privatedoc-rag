import asyncio
import io
import logging
from contextlib import asynccontextmanager
from typing import Annotated

import numpy as np
import torch
import uvicorn
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from PIL import Image
from pydantic import BaseModel

from app.config import settings
from app.pipeline.embeddings.visual_engine import VisualRetrieverEngine
from app.utils.logging_utils import configure_logging

configure_logging()
logger = logging.getLogger("visual_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Eagerly boots and warms up the model weights into the GPU during startup.
    """
    logger.info("Booting Visual Engine API. Loading ColQwen2 into GPU...")

    # 1. Instantiate the engine
    engine = await asyncio.to_thread(VisualRetrieverEngine)

    # 2. FORCE a dummy warmup inference to load weights into VRAM right now
    logger.info("Warming up model weights in VRAM (this will take a moment)...")
    await asyncio.to_thread(engine.embed_query, "warmup query")

    app.state.visual_engine = engine
    app.state.inference_lock = asyncio.Lock()

    logger.info("Visual Engine is fully loaded, warmed up, and ready for traffic.")
    yield

    logger.info("Shutting down Visual Engine API. Releasing VRAM...")
    del app.state.visual_engine
    del app.state.inference_lock
    torch.cuda.empty_cache()


app = FastAPI(title="Visual Embedding Microservice", lifespan=lifespan)


class TextQueryRequest(BaseModel):
    text: str


def get_visual_engine_and_lock(request: Request) -> tuple:
    """
    Extracts the engine and concurrency lock safely.
    Fails predictably with a 503 if uninitialized.
    """
    engine = getattr(request.app.state, "visual_engine", None)
    lock = getattr(request.app.state, "inference_lock", None)
    if not engine or not lock:
        logger.critical(
            "Visual Engine or Lock was not initialized in application state."
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Machine learning models are currently unavailable.",
        )
    return engine, lock


@app.post("/embed/image")
async def embed_image_endpoint(
    file: Annotated[UploadFile, File(...)],
    engine_and_lock: tuple = Depends(get_visual_engine_and_lock),
):
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided.",
        )
    engine, lock = engine_and_lock
    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # Concurrency safety: Only 1 request hits the GPU at a time
        async with lock:
            multi_vector: np.ndarray = await asyncio.to_thread(
                engine.embed_image, image
            )

        return {"vector": multi_vector.tolist()}
    except Exception as e:  # noqa
        logger.error(f"Image embedding failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.post("/embed/text")
async def embed_text_endpoint(
    payload: TextQueryRequest,
    engine_and_lock: tuple = Depends(get_visual_engine_and_lock),
):
    engine, lock = engine_and_lock
    try:
        # Concurrency safety: Only 1 request hits the GPU at a time
        async with lock:
            multi_vector: np.ndarray = await asyncio.to_thread(
                engine.embed_query, payload.text
            )
        return {"vector": multi_vector.tolist()}
    except Exception as e:  # noqa
        logger.error(f"Text embedding failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


if __name__ == "__main__":
    uvicorn.run(
        "app.services.visual_api:app",
        host=settings.visual_api_host,
        port=settings.visual_api_port,
    )
