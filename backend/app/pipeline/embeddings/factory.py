from app.config import settings

from .base import BaseEmbedder
from .ollama_embedder import OllamaEmbedder
from .fastembed_embedder import FastEmbedEmbedder

def create_embedder() -> BaseEmbedder:
    """
    Create the configured embedding provider via Factory Pattern.
    """
    if settings.embedding_provider == "fastembed":
        return FastEmbedEmbedder(model_name=settings.embedding_model)
    elif settings.embedding_provider == "ollama":
        return OllamaEmbedder()
    raise ValueError(f"unsupported  embedding provider: {settings.embedding_model}")
