from app.pipeline.embeddings.factory import create_embedder
from app.pipeline.embeddings.ollama_emdedder import OllamaEmbedder


def test_factory_returns_ollama_embedder():
    embedder = create_embedder()

    assert isinstance(embedder, OllamaEmbedder)
