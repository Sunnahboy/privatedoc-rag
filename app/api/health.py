from fastapi import APIRouter
from app.config import settings

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
def health_check() -> dict:
    """
    Simple health check endpoint.

    Why this matters:
    - Confirms the backend server is alive.
    - Later, Docker and deployment tools can use this to check service status.
    """

    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }