from app.pipeline.embeddings.exception import (
    EmbeddingConnectionError,
    EmbeddingError,
    EmbeddingResponseError,
)


def test_embedding_exceptions():
    assert issubclass(EmbeddingConnectionError, EmbeddingError)
    assert issubclass(EmbeddingResponseError, EmbeddingError)
