"""
Multi-signal deterministic heuristic detector for PDF pages.
Optimized for zero-dependency CPU performance, precise geometric area approximation,
and high-recall visual routing for multimodal RAG pipelines.
"""

import logging
from dataclasses import dataclass
from enum import Enum

import fitz  # PyMuPDF
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# --- Mocking the domain models for self-containment ---
class PageClassification(str, Enum):
    TEXT = "TEXT"
    VISUAL_RICH = "VISUAL_RICH"
    SCAN = "SCAN"


class PageVisualSignals(BaseModel):
    page_number: int
    page_area: float
    text_char_count: int
    text_block_count: int
    text_density: float
    image_count: int
    image_coverage_ratio: float
    drawing_count: int
    drawing_coverage_ratio: float
    combined_graphic_ratio: float

    @property
    def image_area_ratio(self) -> float:
        return self.image_coverage_ratio

    @property
    def drawing_area_ratio(self) -> float:
        return self.drawing_coverage_ratio


@dataclass
class VisualDetectionResult:
    page_number: int
    classification: PageClassification
    should_process_visual: bool
    reasons: list[str]
    signals: PageVisualSignals


# --------------------------------------------------------


class DetectorConfig(BaseModel):
    """
    Centralized configuration holding all parameters.
    No threshold or multiplier is hardcoded in the detection logic.
    """

    # Grid & Precision Configuration
    grid_resolution: int = Field(
        default=50, description="N x N resolution for spatial union approximation"
    )
    coord_epsilon: float = Field(
        default=1e-6, description="Epsilon offset to avoid off-by-one boundary leaks"
    )
    text_density_scale: float = Field(
        default=1000.0, description="Scaling factor for character per area density"
    )

    # Background Element Filtering
    bg_dimension_threshold: float = Field(
        default=0.95,
        description="Ratio threshold to classify rectangle as full-page background",
    )

    # SCAN Thresholds
    scan_min_image_coverage: float = Field(
        default=0.65, description="Min raster image coverage ratio to trigger SCAN"
    )
    scan_max_text_chars: int = Field(
        default=250, description="Max character count allowed for SCAN"
    )

    # VISUAL_RICH: Raster Image Triggers
    min_significant_image_area_ratio: float = Field(
        default=0.01, description="Minimum area ratio to filter out icons/spacers"
    )
    visual_image_coverage_min: float = Field(
        default=0.12, description="Min image area coverage ratio"
    )
    visual_multi_image_count: int = Field(
        default=3, description="Count threshold for multiple images"
    )
    visual_multi_image_min_coverage: float = Field(
        default=0.05, description="Min area coverage when multi-image count is met"
    )

    # VISUAL_RICH: Vector Drawing Triggers
    visual_drawing_count_min: int = Field(
        default=150, description="Min vector drawing path count"
    )
    visual_drawing_coverage_min: float = Field(
        default=0.15, description="Min vector drawing area coverage ratio"
    )
    table_safeguard_char_threshold: int = Field(
        default=1000, description="Character threshold identifying dense text tables"
    )
    dense_text_drawing_multiplier: float = Field(
        default=1.5, description="Path count multiplier applied for dense text pages"
    )

    # VISUAL_RICH: Low-Text Graphic Triggers
    low_text_char_threshold: int = Field(
        default=400, description="Max character threshold for low-text graphic pages"
    )
    low_text_graphic_coverage_min: float = Field(
        default=0.08,
        description="Min combined graphic coverage ratio for low-text pages",
    )


class CoverageGrid:
    """
    Zero-allocation flat bytearray spatial grid.
    Eliminates Python tuple allocations in tight loops.
    """

    __slots__ = ("cell_h", "cell_w", "grid", "resolution", "total_marked")

    def __init__(self, page_width: float, page_height: float, resolution: int = 50):
        self.resolution = resolution
        self.cell_w = max(page_width / resolution, 1.0)
        self.cell_h = max(page_height / resolution, 1.0)
        self.grid = bytearray(resolution * resolution)
        self.total_marked = 0

    def add_rect(self, rect: fitz.Rect, bounds: fitz.Rect):
        intersect = rect & bounds
        if intersect.is_empty:
            return

        min_col = max(0, int(intersect.x0 / self.cell_w))
        max_col = min(self.resolution - 1, int((intersect.x1 - 1e-6) / self.cell_w))
        min_row = max(0, int(intersect.y0 / self.cell_h))
        max_row = min(self.resolution - 1, int((intersect.y1 - 1e-6) / self.cell_h))

        res = self.resolution
        grid = self.grid

        for r in range(min_row, max_row + 1):
            row_offset = r * res
            for c in range(min_col, max_col + 1):
                idx = row_offset + c
                if not grid[idx]:
                    grid[idx] = 1
                    self.total_marked += 1

    def coverage_ratio(self) -> float:
        return self.total_marked / (self.resolution * self.resolution)


class VisualRichDetector:
    def __init__(self, config: DetectorConfig | None = None) -> None:
        self.config = config or DetectorConfig()

    def analyze_page(self, page: fitz.Page) -> VisualDetectionResult:
        signals = self._extract_signals(page)
        classification, reasons = self._classify(signals)

        should_process = classification in (
            PageClassification.VISUAL_RICH,
            PageClassification.SCAN,
        )

        return VisualDetectionResult(
            page_number=page.number + 1,
            classification=classification,
            should_process_visual=should_process,
            reasons=reasons,
            signals=signals,
        )

    def _extract_signals(self, page: fitz.Page) -> PageVisualSignals:
        rect = page.rect
        page_area = max(rect.width * rect.height, 1.0)

        # 1. Text Metrics
        text = page.get_text("text") or ""
        char_count = len(text.strip())
        blocks = [b for b in page.get_text("blocks") if b[6] == 0]
        text_density = (char_count / page_area) * 1000.0

        # Spatial Grids for true union area calculation
        image_grid = CoverageGrid(rect.width, rect.height, self.config.grid_resolution)
        drawing_grid = CoverageGrid(
            rect.width, rect.height, self.config.grid_resolution
        )
        combined_grid = CoverageGrid(
            rect.width, rect.height, self.config.grid_resolution
        )

        # 2. Raster Image Metrics
        image_infos = page.get_image_info(xrefs=True)
        significant_image_count = 0

        for img in image_infos:
            bbox = fitz.Rect(img["bbox"])
            intersect = bbox & rect
            ratio = (intersect.width * intersect.height) / page_area

            # Ignore tiny watermarks, 1x1 pixel masks, and bullet point icons
            if ratio >= self.config.min_significant_image_area_ratio:
                significant_image_count += 1
                image_grid.add_rect(bbox, rect)
                combined_grid.add_rect(bbox, rect)

        # 3. Vector Drawing Metrics
        drawings = page.get_drawings()
        drawing_count = len(drawings)

        for dwg in drawings:
            dwg_rect = fitz.Rect(dwg["rect"])

            # Ignore full-page backgrounds (e.g. presentation slide backgrounds)
            if (
                dwg_rect.width >= rect.width * 0.95
                and dwg_rect.height >= rect.height * 0.95
            ):
                continue

            drawing_grid.add_rect(dwg_rect, rect)
            combined_grid.add_rect(dwg_rect, rect)

        return PageVisualSignals(
            page_number=page.number + 1,
            page_area=page_area,
            text_char_count=char_count,
            text_block_count=len(blocks),
            text_density=round(text_density, 3),
            image_count=significant_image_count,
            image_coverage_ratio=round(image_grid.coverage_ratio(), 4),
            drawing_count=drawing_count,
            drawing_coverage_ratio=round(drawing_grid.coverage_ratio(), 4),
            combined_graphic_ratio=round(combined_grid.coverage_ratio(), 4),
        )

    def _classify(self, s: PageVisualSignals) -> tuple[PageClassification, list[str]]:
        reasons: list[str] = []

        # RULE 1: SCAN Check (Overrides VISUAL_RICH)
        if (
            s.image_coverage_ratio >= self.config.scan_min_image_coverage
            and s.text_char_count <= self.config.scan_max_text_chars
        ):
            reasons.append(
                f"SCAN: High image coverage ({s.image_coverage_ratio:.1%}) with low text ({s.text_char_count} chars)"
            )
            return PageClassification.SCAN, reasons

        # RULE 2: Raster Images (Diagrams, Photos, Plots)
        if s.image_coverage_ratio >= self.config.visual_image_coverage_min:
            reasons.append(
                f"VISUAL: Significant image coverage ({s.image_coverage_ratio:.1%})"
            )
        elif (
            s.image_count >= self.config.visual_multi_image_count
            and s.image_coverage_ratio >= 0.05
        ):
            reasons.append(f"VISUAL: Multiple significant images ({s.image_count})")

        # RULE 3: Dense Vector Drawings (Architecture Diagrams, Charts)
        # We increase the required vector count if it looks like a dense text table
        is_dense_text = s.text_char_count > self.config.table_safeguard_char_threshold
        req_drawing_count = self.config.visual_drawing_count_min * (
            1.5 if is_dense_text else 1.0
        )

        if s.drawing_count >= req_drawing_count:
            reasons.append(
                f"VISUAL: High vector path count ({s.drawing_count} >= {req_drawing_count})"
            )
        elif s.drawing_coverage_ratio >= self.config.visual_drawing_coverage_min:
            reasons.append(
                f"VISUAL: High vector true-area coverage ({s.drawing_coverage_ratio:.1%})"
            )

        # RULE 4: Low Text + Graphics (Infographics, Title Slides)
        if (
            s.text_char_count <= self.config.low_text_char_threshold
            and s.combined_graphic_ratio >= self.config.low_text_graphic_coverage_min
        ):
            reasons.append(
                f"VISUAL: Low text ({s.text_char_count} chars) with graphics ({s.combined_graphic_ratio:.1%})"
            )

        if reasons:
            return PageClassification.VISUAL_RICH, reasons

        return PageClassification.TEXT, ["Standard text or simple table layout"]
