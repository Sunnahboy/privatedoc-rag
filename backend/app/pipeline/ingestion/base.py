from abc import ABC, abstractmethod
from pathlib import Path

from .models import IngestionResult


class BaseIngestionPipeline(ABC):
    @abstractmethod
    async def ingest(
        self,
        document_id: str,
        file_path: Path,
    ) -> IngestionResult: ...
