"""
Unit tests for VisualRichDetector heuristic calculations.
"""

import fitz
import pytest
from app.pipeline.detector.models import PageClassification
from app.pipeline.detector.visual_detector import DetectorConfig, VisualRichDetector


@pytest.fixture
def detector() -> VisualRichDetector:
    return VisualRichDetector(DetectorConfig())


def _reload_doc(doc: fitz.Document) -> tuple[fitz.Document, fitz.Page]:
    """
    Helper to save and reload the document in memory.
    This guarantees PyMuPDF's get_drawings() and get_image_info()
    evaluate the finalized PDF stream exactly as if it were read from disk.
    """
    doc_bytes = doc.write()
    doc.close()
    new_doc = fitz.open("pdf", doc_bytes)
    return new_doc, new_doc[0]


def test_pure_text_page(detector: VisualRichDetector):
    """A standard document page with paragraphs should classify as TEXT."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)  # Standard Letter

    # Insert 10 lines of standard body text
    for i in range(10):
        page.insert_text(
            fitz.Point(50, 50 + (i * 20)),
            "Software architecture patterns establish structural integrity for enterprise applications.",
        )

    doc, page = _reload_doc(doc)
    result = detector.analyze_page(page)

    assert result.classification == PageClassification.TEXT
    assert not result.should_process_visual
    assert result.signals.image_count == 0
    assert result.signals.drawing_count == 0
    doc.close()


def test_diagram_vector_page(detector: VisualRichDetector):
    """A page with limited text but many vector shapes should classify as VISUAL_RICH."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)

    # Small label
    page.insert_text(fitz.Point(50, 50), "Figure 2.1: Microservices Architecture")

    # Draw boxes and lines
    shape = page.new_shape()
    for i in range(25):
        shape.draw_rect(
            fitz.Rect(60 + i * 10, 100 + i * 10, 180 + i * 10, 160 + i * 10)
        )
        shape.draw_line(fitz.Point(50, 100 + i * 10), fitz.Point(300, 100 + i * 10))

    # CRITICAL: You must apply a stroke color and finish the shape for it to exist!
    shape.finish(color=(0, 0, 0), width=1.0)
    shape.commit()

    # PyMuPDF requires a save/reload to fully parse the new drawing stream
    pdf_bytes = doc.tobytes()
    doc.close()

    # Reload and test
    doc_reloaded = fitz.open("pdf", pdf_bytes)
    page_reloaded = doc_reloaded[0]

    result = detector.analyze_page(page_reloaded)

    assert result.classification == PageClassification.VISUAL_RICH
    assert result.should_process_visual
    assert result.signals.drawing_area_ratio > 0.0

    doc_reloaded.close()


def test_scanned_page(detector: VisualRichDetector):
    """A page covered almost entirely by a raster image with no text should classify as SCAN."""
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)

    # CRITICAL: Modern PyMuPDF requires a Rect object for dimensions, not raw integers
    pix = fitz.Pixmap(fitz.csRGB, fitz.Rect(0, 0, 100, 100), False)
    pix.clear_with(255)  # Give it a white background so it's a valid image block

    # Insert it across the entire page
    page.insert_image(page.rect, pixmap=pix)

    result = detector.analyze_page(page)

    assert result.classification == PageClassification.SCAN
    assert result.should_process_visual
    assert result.signals.image_area_ratio >= 0.95
    assert result.signals.text_char_count == 0
    doc.close()


def test_background_color_rect_ignored(detector: VisualRichDetector):
    """A tinted page background should not trigger false positive drawing counts."""
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)

    # Draw a full page background tint
    shape = page.new_shape()
    shape.draw_rect(page.rect)
    shape.finish(color=(0.95, 0.95, 0.95), fill=(0.95, 0.95, 0.95))
    shape.commit()

    # Add regular text
    page.insert_text(
        fitz.Point(50, 50), "Standard chapter introductory text goes here."
    )

    doc, page = _reload_doc(doc)
    result = detector.analyze_page(page)

    # Drawing area ratio should be 0.0 because the full-page rect was ignored
    assert result.signals.drawing_area_ratio == 0.0
    assert result.classification == PageClassification.TEXT
    doc.close()
