class IngestionError(Exception):
    """Base ingestion pipeline exception."""


class ExtractionStageError(IngestionError):
    """Extraction stage failed."""


class CleaningStageError(IngestionError):
    """Cleaning stage failed."""


class ChunkingStageError(IngestionError):
    """Chunking stage failed."""


class EmbeddingStageError(IngestionError):
    """Embedding stage failed."""


class IndexingStageError(IngestionError):
    """Indexing stage failed."""