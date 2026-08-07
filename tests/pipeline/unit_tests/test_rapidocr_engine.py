import numpy as np
from app.pipeline.ocr import RapidOCREngine


def test_rapidocr_returns_empty_on_empty_image():
    engine = RapidOCREngine()
    empty_image = np.array([])
    assert engine.extract(empty_image) == ""


# Testing actual OCR extraction should ideally be an integration test
# as it requires downloading models, but the abstraction holds.
