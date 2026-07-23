class EmbeddingError(Exception):
    """Base embedding exception."""


class EmbeddingConnectionError(EmbeddingError):
    """Unable to connect to embedding service."""


class EmbeddingResponseError(EmbeddingError):
    """Embedding service returned an invalid response."""
