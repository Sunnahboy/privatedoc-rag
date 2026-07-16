from pathlib import Path

from .base import BaseExtractor
from .docx_extractor import DOCXExtractor
from .markdown_extractor import MarkdownExtractor
from .pdf_extractor import PDFExtractor
from .pptx_extractor import PPTExtractor
from .txt_extractor import TXTExtractor


class ExtractorFactory:
    """

    Returns the correct extractor for a file type.

    The rest of the pipeline never checks
    file extensions directory.
    """

    @staticmethod
    def create(file_path: Path) -> BaseExtractor:

        extension = file_path.suffix.lower()

        mapping = {
            ".pdf": PDFExtractor,
            ".txt": TXTExtractor,
            ".md": MarkdownExtractor,
            ".pptx": PPTExtractor,
            ".docx": DOCXExtractor,
        }
        extractor_class = mapping.get(extension)

        if extractor_class is None:
            raise ValueError(f"No extractor registered for {extension}")

        return extractor_class()
