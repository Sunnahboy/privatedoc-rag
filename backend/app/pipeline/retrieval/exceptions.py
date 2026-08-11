class RetrievalError(Exception):
    """Base retrieve exception."""


class SearchError(RetrievalError):
    """Raised when vector search fails."""
