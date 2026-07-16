from pathlib import Path

from app.pipeline.extraction.factory import ExtractorFactory
from app.pipeline.extraction.pdf_extractor import PDFExtractor


def test_factory_returns_pdf_extractor_for_pdf_files():
    extractor = ExtractorFactory.create(Path("report.pdf"))

    assert isinstance(extractor, PDFExtractor)
