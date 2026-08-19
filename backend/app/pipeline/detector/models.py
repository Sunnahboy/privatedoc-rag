"""
Data models and schemas for visual page classification and routing"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PageClassification(str, Enum):
    TEXT = "TEXT"  # Standard text/prose page (no visual index needed)
    VISUAL_RICH = "VISUAL_RICH"  # Diagrams, charts, tables, vector graphics, figures
    SCAN = "SCAN"  # Full-page raster image / scanned page with low digital text


class PageVisualSignals(BaseModel):
    """Raw physical metrics extracted from a single PyMUPDF page."""

    page_number: int
    page_width: float
    page_height: float
    page_area: float

    # Text Metrics
    text_char_count: int
    text_word_count: int
    text_block_count: int
    text_density: float = Field(
        description="Characters per 1,000 square points of page area."
    )

    # Raster Image Metrics
    image_count: int
    total_image_area: float
    image_area_ratio: float = Field(
        description="Fraction of total page area covered by raster images [0.0 - 1.0]."
    )
    has_large_image: bool = Field(
        description="True if any single raster image covers > 40% of the page."
    )

    # Vector Drawing Metrics (Lines, Shapes, Tables, Curves)
    drawing_count: int
    total_drawing_area: float
    drawing_area_ratio: float = Field(
        description="Fraction of total page area covered by vector drawings [0.0 - 1.0]."
    )


class VisualDetectionResult(BaseModel):
    """Complete diagnostic result emitted by the VisualRichDetector."""

    page_number: int
    classification: PageClassification
    should_process_visual: bool
    reasons: list[str] = Field(
        default_factory=list,
        description="Explainable triggers explaining why this classification was assigned.",
    )
    signals: PageVisualSignals


class DocumentVisualJobMessage(BaseModel):
    """RabbitMQ message payload published to 'document.visual.process'."""

    document_id: str
    page_number: int
    classification: PageClassification
    reasons: list[str]
    signals: dict[str, Any]
