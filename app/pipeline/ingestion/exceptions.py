class IngestionError(Exception):
    """Base ingestion pipeline exception."""


class ExtractionError(IngestionError):
    """Extraction stage failed."""


class CleaningError(IngestionError):
    """Cleaning stage failed."""


class ChunkingError(IngestionError):
    """Chunking stage failed."""


class EmbeddingError(IngestionError):
    """Embedding stage failed."""


class IndexingError(IngestionError):
    """Indexing stage failed."""