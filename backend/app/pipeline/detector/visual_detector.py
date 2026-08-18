"""
Multi-signal deterministic heuristic detector for PDF pages.
Analyzes layout structure, text density, raster images, and vector drawing paths.
"""

import logging

import fitz  # PyMuPDF
from app.pipeline.detector.models import (
    PageClassification,
    PageVisualSignals,
    VisualDetectionResult,
)
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class DetectorConfig(BaseModel):
    """
    Configurable heuristic thresholds.
    Allows systematic tuning and benchmarking without changing code logic.
    """

    # SCAN Thresholds
    scan_min_image_coverage: float = 0.70  # >= 70% page covered by raster image
    scan_max_text_chars: int = 150  # <= 150 characters of digital text

    # VISUAL_RICH: Raster Image Triggers
    visual_image_coverage_min: float = 0.12  # >= 12% page covered by images
    visual_multi_image_count: int = 2  # >= 2 images with non-trivial area

    # VISUAL_RICH: Vector Drawing Triggers (Architectural diagrams, charts, tables)
    visual_drawing_count_min: int = 40  # >= 40 vector path elements
    visual_drawing_coverage_min: float = 0.15  # >= 15% page area covered by drawings

    # VISUAL_RICH: Low-Text Graphic Density
    low_text_char_threshold: int = 350  # Pages with limited text
    low_text_graphic_coverage_min: float = 0.08  # Combined image/drawing coverage >= 8%


class VisualRichDetector:
    """
    Evaluates PyMuPDF pages using lightweight CPU operations to decide
    whether a page requires visual indexing (ColPali/ColQwen/OCR).
    """

    def __init__(self, config: DetectorConfig | None = None) -> None:
        self.config = config or DetectorConfig()

    def analyze_page(self, page: fitz.Page) -> VisualDetectionResult:
        """
        Extracts multi-modal signals and classifies the page into
        TEXT, VISUAL_RICH, or SCAN.
        """
        signals = self._extract_signals(page)
        classification, reasons = self._classify(signals)

        should_process = classification in (
            PageClassification.VISUAL_RICH,
            PageClassification.SCAN,
        )

        return VisualDetectionResult(
            page_number=signals.page_number,
            classification=classification,
            should_process_visual=should_process,
            reasons=reasons,
            signals=signals,
        )

    def _extract_signals(self, page: fitz.Page) -> PageVisualSignals:
        """Extracts physical measurements without loading heavy image bitmaps."""
        rect = page.rect
        page_width = float(rect.width)
        page_height = float(rect.height)
        page_area = max(page_width * page_height, 1.0)

        # 1. Text Metrics
        text = page.get_text("text") or ""
        char_count = len(text.strip())
        word_count = len(text.split())
        blocks = [
            b for b in page.get_text("blocks") if b[6] == 0
        ]  # Type 0 = Text block
        block_count = len(blocks)
        text_density = (char_count / page_area) * 1000.0

        # 2. Raster Image Metrics
        image_infos = page.get_image_info(xrefs=True)
        image_count = len(image_infos)
        total_image_area = 0.0
        has_large_image = False

        for img in image_infos:
            bbox = fitz.Rect(img["bbox"])
            # Bound within page dimensions
            intersect = bbox & rect
            area = intersect.width * intersect.height
            total_image_area += area
            if (area / page_area) >= 0.40:
                has_large_image = True

        image_area_ratio = min(total_image_area / page_area, 1.0)

        # 3. Vector Drawing Metrics (Paths, Rectangles, Bezier Curves)
        drawings = page.get_drawings()
        drawing_count = len(drawings)
        total_drawing_area = 0.0

        for dwg in drawings:
            dwg_rect = fitz.Rect(dwg["rect"])

            # Filter out full-page background color rectangles
            is_full_page_bg = (
                dwg_rect.width >= page_width * 0.96
                and dwg_rect.height >= page_height * 0.96
            )
            if is_full_page_bg:
                continue

            intersect = dwg_rect & rect
            total_drawing_area += intersect.width * intersect.height

        drawing_area_ratio = min(total_drawing_area / page_area, 1.0)

        return PageVisualSignals(
            page_number=page.number + 1,  # 1-based indexing
            page_width=page_width,
            page_height=page_height,
            page_area=page_area,
            text_char_count=char_count,
            text_word_count=word_count,
            text_block_count=block_count,
            text_density=round(text_density, 3),
            image_count=image_count,
            total_image_area=round(total_image_area, 2),
            image_area_ratio=round(image_area_ratio, 4),
            has_large_image=has_large_image,
            drawing_count=drawing_count,
            total_drawing_area=round(total_drawing_area, 2),
            drawing_area_ratio=round(drawing_area_ratio, 4),
        )

    def _classify(self, s: PageVisualSignals) -> tuple[PageClassification, list[str]]:
        """Evaluates heuristic rules in order of priority."""
        reasons: list[str] = []

        # RULE 1: Scanned Document Page Check
        # High image coverage + virtually no digital text layer
        if (
            s.image_area_ratio >= self.config.scan_min_image_coverage
            and s.text_char_count <= self.config.scan_max_text_chars
        ):
            reasons.append(
                f"SCAN: Image coverage ({s.image_area_ratio:.1%}) >= {self.config.scan_min_image_coverage:.1%} "
                f"with low text char count ({s.text_char_count})"
            )
            return PageClassification.SCAN, reasons

        # RULE 2: Significant Raster Images (Figures, Photos, Embedded Charts)
        if s.image_area_ratio >= self.config.visual_image_coverage_min:
            reasons.append(
                f"VISUAL: Image area ratio ({s.image_area_ratio:.1%}) >= threshold ({self.config.visual_image_coverage_min:.1%})"
            )
        elif (
            s.image_count >= self.config.visual_multi_image_count
            and s.image_area_ratio >= 0.05
        ):
            reasons.append(
                f"VISUAL: Multiple images ({s.image_count}) with non-trivial coverage ({s.image_area_ratio:.1%})"
            )

        # RULE 3: Dense Vector Drawings (Architecture Diagrams, Flowcharts, Complex Tables)
        if s.drawing_count >= self.config.visual_drawing_count_min:
            reasons.append(
                f"VISUAL: High vector drawing count ({s.drawing_count} paths >= {self.config.visual_drawing_count_min})"
            )
        elif s.drawing_area_ratio >= self.config.visual_drawing_coverage_min:
            reasons.append(
                f"VISUAL: High vector drawing coverage ({s.drawing_area_ratio:.1%} >= {self.config.visual_drawing_coverage_min:.1%})"
            )

        # RULE 4: Low Text Density combined with Graphic Elements
        # Catches slides, title callouts with diagrams, and sparse infographics
        combined_graphic_ratio = min(s.image_area_ratio + s.drawing_area_ratio, 1.0)
        if (
            s.text_char_count <= self.config.low_text_char_threshold
            and combined_graphic_ratio >= self.config.low_text_graphic_coverage_min
        ):
            reasons.append(
                f"VISUAL: Low text ({s.text_char_count} chars) combined with graphic elements "
                f"({combined_graphic_ratio:.1%} total graphic ratio)"
            )

        if reasons:
            return PageClassification.VISUAL_RICH, reasons

        # RULE 5: Default standard prose / pure text
        return PageClassification.TEXT, ["Standard text layout"]
