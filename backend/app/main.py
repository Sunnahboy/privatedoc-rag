import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from app.pipeline.embeddings.visual_engine import VisualRetrieverEngine

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.document import router as documents_router
from app.api.health import router as health_router
from app.api.rag_router import router as rag_router
from app.api.reader_router import router as reader_router
from app.config import settings
from app.messaging.connection import rabbitmq_manager
from app.api.chat import router as chat_router
from app.qdrant import setup_qdrant_collections
from app.utils.logging_utils import configure_logging
from app.database import engine
configure_logging()
logger = logging.getLogger(__name__)





# A lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Handles backend startup and shutdown tasks.
    """
    logger.info("starting %s v%s", settings.app_name, settings.app_version)
   #Initialize Visual Engine & Qdrant Collections
    VisualRetrieverEngine._initialize_engine()
    # 2. Database initialization
    logger.info("Database initialized")
    await setup_qdrant_collections()  # check if 'documents_visual' exists,
    # Initialize RabbitMQ Manager so the channel pool is ready for publishers
    await rabbitmq_manager.initialize()

    yield

    #    SHUTDOWN logic
    logger.info("Shutting down %s", settings.app_name)

    # Gracefully close connections and drain the pool
    await rabbitmq_manager.close()
    await engine.dispose()#dispose of the async engine on shutdown


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Self-hosted RAG system using local LLM inference, "
    "vector search, and  grounded responses with citations.",
    lifespan=lifespan,
)

# cors allows the frontend to call the backend
app.add_middleware(
    # later change to i.e "http://localhost:xx",
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
#  exposes your PDF files so the Next.js v
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

app.include_router(health_router)
app.include_router(documents_router)
app.include_router(rag_router)
app.include_router(reader_router)
app.include_router(chat_router)


@app.get("/")
def root() -> dict:
    """
    Root endpoint.

    this is not the main API.
    Simply confirms the backend is reachable
    """
    return {
        "message": "PrivateDoc RAG backend is running.",
        "docs": "/docs",
        "health": "/health",
        "documents": "/document",
        "rag": "/rag/ask",
    }
