from abc import ABC, abstractmethod
from app.pipeline.extraction.models import ExtractionResult

from .models import CleaningResult


class BaseCleaner(ABC):
    """
    Every cleaner follows this contract
    """

    @abstractmethod
    async def clean(
        self,
        extraction: ExtractionResult,
    ) -> CleaningResult:
        ...
