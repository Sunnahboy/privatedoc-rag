from abc import ABC, abstractmethod
from pathlib import Path

from .models import ExtractionResult


class BaseExtractor(ABC):
    """
    Contract that every extractor must follow
    """

    @abstractmethod
    async def extract(self, file_path: Path) -> ExtractionResult:
        """
        Extract text from the document.

        Args:
            file_path: The Path object pointing to the target file.

        Returns:
            ExtractionResult object containing the parsed metadata.
        """
        ...
