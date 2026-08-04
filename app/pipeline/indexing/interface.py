from abc import ABC, abstractmethod

from app.pipeline.retrieval.models import RetrievedChunk

from .models import IndexingRequest, IndexingResult


class BaseIndexer(ABC):
    @abstractmethod
    async def index(
        self,
        request: IndexingRequest,
    ) -> IndexingResult:
        """ "
        Index embeddings into the vector database.
        """
        ...


class BaseSparseIndex(ABC):
    """Abstract interface for sparse indexes."""

    @abstractmethod
    async def add_documents(self, chunks) -> None:
        """Index document chunks."""

    @abstractmethod
    async def search(
        self,
        query: str,
        top_k: int,
    ) -> list[RetrievedChunk]:
        """Search indexed documents."""

    @abstractmethod
    async def delete_document(
        self,
        document_id: str,
    ) -> None:
        """Delete one document from the index."""

    @abstractmethod
    async def close(self) -> None:
        """Release resources."""
