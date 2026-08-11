from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from app.pipeline.extraction.pdf_extractor import PDFExtractor
from app.pipeline.ocr.base import BaseOCR


class MockOCR(BaseOCR):
    def extract(self, image: np.ndarray) -> str:
        return "MOCKED_OCR_TEXT"


@pytest.fixture
def pdf_extractor():
    mock_ocr = MockOCR()
    return PDFExtractor(ocr_engine=mock_ocr)


def test_pdf_extractor_skips_ocr_when_sufficient_text(pdf_extractor):
    mock_page = MagicMock()
    # Provide realistic rect dimensions so page_area calculation works
    mock_page.rect.width = 600
    mock_page.rect.height = 800
    mock_page.get_images.return_value = []  # No images

    sufficient_text = "This is a document that has plenty of digital text so it should skip OCR completely."

    assert pdf_extractor._should_run_ocr(mock_page, sufficient_text) is False


def test_pdf_extractor_triggers_ocr_when_no_text_but_has_image(pdf_extractor):
    mock_page = MagicMock()
    mock_page.get_images.return_value = [{"xref": 1}]  # Page has images
    mock_page.rect.width = 100
    mock_page.rect.height = 100
    # Image covers 100% of the page
    mock_page.get_image_info.return_value = [{"bbox": (0, 0, 100, 100)}]

    assert pdf_extractor._should_run_ocr(mock_page, "") is True


def test_process_single_page_uses_ocr_fallback(pdf_extractor):
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.get_text.return_value = ""  # No native text

    # Mock the internal methods to avoid actual fitz image processing
    # Mock the internal methods to avoid actual fitz image processing
    with (
        patch.object(pdf_extractor, "_should_run_ocr", return_value=True),
        patch.object(
            pdf_extractor,
            "_page_to_numpy",
            return_value=np.zeros((100, 100, 3), dtype=np.uint8),
        ),
    ):
        mock_doc.load_page.return_value = mock_page

        result = pdf_extractor._process_single_page(mock_doc, 0, 0)

        # The result should be from our MockOCR engine
        assert result == "MOCKED_OCR_TEXT"
