from app.config import settings

from .base import BaseEmbedder
from .ollama_emdedder import OllamaEmbedder


def create_embedder() -> BaseEmbedder:
    """
    Create the configured embedding provider.
     -for now one provider
    """

    if settings.embedding_provider == "ollama":
        return OllamaEmbedder()
    raise ValueError(f"unsupported  embedding provider: {settings.embedding_model}")
