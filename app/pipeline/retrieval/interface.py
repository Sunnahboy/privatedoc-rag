from abc import ABC, abstractmethod

from .models import RetrievalResult


class BaseRetriever(ABC):
    @abstractmethod
    async def retrieve(
        self,
        query: str,
        top_k: int,
    ) -> RetrievalResult:
        """
        Retrieve relevant chunks.
        """

        ...
