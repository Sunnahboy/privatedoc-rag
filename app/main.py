import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.health import router as health_router
from app.config import settings
from app.utils.logging_utils import configure_logging
from contextlib import asynccontextmanager
configure_logging()
logger = logging.getLogger(__name__)

# A lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles backend startup and shutdown tasks.
    """
    # ----Startup logic------
    logger.info("starting %s v%s", settings.app_name,settings.app_version)

    # TODO: Put my connection checks here
    # - Verify database connection
    # - Verify Qdrant connection
    # - Verify Ollama connection

    yield 

    #----SHUTDOWN logic----
    # TODO: cleanup code (i.e., closing db connections)
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Self-hosted RAG system using local LLM inference, vector search, and source ",
    lifespan=lifespan
)

# cors allows the frontend to call the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)


@app.get("/")
def root() -> dict:
    """
    Root endpoint.

    this is not the main API.
    Simply confirms the backend is reachable
    """
    return {
        "message":"PrivateDoc RAG backend is running.",
        "docs":"/docs",
        "health":"/health",
    }