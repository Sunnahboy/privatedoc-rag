from abc import ABC, abstractmethod

from .models import RetrievalResult, RetrievedChunk


class BaseRetriever(ABC):
    """Interface for retrieval backends that must enforce tenant isolation."""

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        user_id: str,
        top_k: int | None = None,
        document_id: str | None = None,
        document_ids: list[str] | None = None,
        **kwargs,
    ) -> RetrievalResult:
        """
        Retrieve relevant chunks owned by ``user_id``.

        ``user_id`` is deliberately required rather than optional: a retrieval
        implementation must never be able to issue an unscoped search.
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
