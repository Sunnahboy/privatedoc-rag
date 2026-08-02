from abc import ABC, abstractmethod

from .models import IngestionResult


class BaseIngestionPipeline(ABC):
    @abstractmethod
    async def ingest(
        self,
        document_id: str,
        files_path: str,
    ) -> IngestionResult: ...
