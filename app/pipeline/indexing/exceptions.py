class IndexingError(Exception):
    """Base exception for indexing errors."""

class CollectionError(IndexError):
    """Raised when collections operations fail."""

class UpsertError(IndexingError):
    """Raised when the indexing points fail."""