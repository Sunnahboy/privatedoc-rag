from abc import ABC, abstractmethod

from .models import RetrievalResult, RetrievedChunk


class BaseRetriever(ABC):
    """Interface for broad search engines (Qdrant, Tantivy)."""

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        document_id: str | None = None,
        limit: int = 5,  
        **kwargs,
    ) -> RetrievalResult:
        """
        Retrieve relevant chunks.
        """

        ...


class BaseReranker(ABC):
    """Interface for deep semantic re-scoring (Cross-Encoders)."""

    @abstractmethod
    def rerank(
        self, query: str, chunks: list[RetrievedChunk], top_k: int  | None,
    ) -> list[RetrievedChunk]:
        """
        Takes a broad list of chunks and re-scores them against the query.
        """
        ...
