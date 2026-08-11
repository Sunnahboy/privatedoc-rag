import asyncio
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import fitz
import numpy as np
from app.config import settings
from app.pipeline.ocr import BaseOCR, RapidOCREngine

from .base import BaseExtractor
from .models import ExtractionResult

logger = logging.getLogger(__name__)

_MIN_DIGITAL_TEXT_WORDS = settings.min_digital_text_words
_OCR_DPI = int(os.environ.get("PDF_OCR_DPI", settings.pdf_ocr_dpi))


def _chunk_ranges(total: int, num_chunks: int) -> list[range]:
    if total == 0 or num_chunks == 0:
        return []
    base, remainder = divmod(total, num_chunks)
    ranges, start = [], 0
    for i in range(num_chunks):
        size = base + (1 if i < remainder else 0)
        if size == 0:
            continue
        ranges.append(range(start, start + size))
        start += size
    return ranges


class PDFExtractor(BaseExtractor):
    """
    PDF extraction strategy using native text with an injected OCR fallback.
    """

    def __init__(self, ocr_engine: BaseOCR | None = None):
        """
        Initialize the PDF Extractor.

        Args:
            ocr_engine: An instance of BaseOCR. Defaults to RapidOCREngine if None.
        """
        self.ocr = ocr_engine or RapidOCREngine()

    async def extract(self, file_path: Path) -> ExtractionResult:
        if not file_path.exists():
            raise FileNotFoundError(file_path)

        return await asyncio.to_thread(
            self._sync_extract,
            file_path,
        )

    def _sync_extract(self, file_path: Path) -> ExtractionResult:
        try:
            file_bytes = file_path.read_bytes()

            with fitz.open(stream=file_bytes, filetype="pdf") as document:
                total_pages = document.page_count
                metadata = dict(document.metadata)

            print(f"[PDF] {file_path.name}: {total_pages} page(s) detected.")

            if total_pages == 0:
                return ExtractionResult(
                    text="",
                    total_pages=0,
                    metadata=metadata,
                )

            max_workers = min(total_pages, settings.pdf_ocr_max_concurrent)
            page_ranges = _chunk_ranges(total_pages, max_workers)

            print(
                f"[PDF] Using {len(page_ranges)} worker(s) for {total_pages} page(s): "
                + ", ".join(
                    f"worker {i} -> pages {r.start + 1}-{r.stop}"
                    for i, r in enumerate(page_ranges)
                )
            )

            overall_start = time.perf_counter()

            with ThreadPoolExecutor(
                max_workers=len(page_ranges),
                thread_name_prefix="pdf_page_worker",
            ) as executor:
                futures = [
                    executor.submit(
                        self._process_page_range,
                        file_bytes,
                        page_range,
                        worker_id,
                    )
                    for worker_id, page_range in enumerate(page_ranges)
                ]

                chunk_results = [future.result() for future in futures]

            pages = [text for chunk in chunk_results for text in chunk]

            print(
                f"[PDF] {file_path.name}: extraction finished in "
                f"{time.perf_counter() - overall_start:.2f}s "
                f"({sum(1 for p in pages if p)}/{total_pages} pages produced text)."
            )

            return ExtractionResult(
                text="\n\n".join(filter(None, pages)).strip(),
                total_pages=total_pages,
                metadata=metadata,
            )

        except fitz.FileDataError as exc:
            raise RuntimeError(f"Invalid PDF: {file_path}") from exc

    def _process_page_range(
        self,
        file_bytes: bytes,
        page_range: range,
        worker_id: int = 0,
    ) -> list[str]:
        results: list[str] = []
        print(
            f"[worker {worker_id}] opening PDF for pages "
            f"{page_range.start + 1}-{page_range.stop}"
        )

        try:
            with fitz.open(stream=file_bytes, filetype="pdf") as document:
                for page_number in page_range:
                    page_start = time.perf_counter()

                    # Catch errors PER PAGE so one bad page doesn't kill the whole worker chunk
                    try:
                        text = self._process_single_page(
                            document, page_number, worker_id
                        )
                        results.append(text)
                        print(
                            f"[worker {worker_id}] page {page_number + 1} done "
                            f"in {time.perf_counter() - page_start:.2f}s "
                            f"({len(text)} chars)"
                        )
                    except Exception:
                        logger.exception("Failed processing page %d", page_number + 1)
                        print(
                            f"[worker {worker_id}] FAILED processing page {page_number + 1}"
                        )
                        results.append("")

        except Exception:
            logger.exception("Worker %d failed to open document", worker_id)
            results.extend(
                "" for _ in range(page_range.stop - page_range.start - len(results))
            )

        print(f"[worker {worker_id}] finished range, {len(results)} page(s) processed")

        return results

    def _process_single_page(
        self,
        document: fitz.Document,
        page_number: int,
        worker_id: int = 0,
    ) -> str:
        """Extract one page using native text with OCR fallback."""
        try:
            page = document.load_page(page_number)
            text = page.get_text().strip()

            if not self._should_run_ocr(page, text):
                return text

            image_np = self._page_to_numpy(page)

            # Fast Path: Skip blank/pure white pages even if we generated an image
            if image_np.size == 0 or np.mean(image_np) > 252:
                return text

            # Inject the image into the abstracted OCR module
            ocr_text = self.ocr.extract(image_np)

            return ocr_text or text

        except Exception:
            logger.exception("Failed processing page %d", page_number + 1)
            return ""

    def _should_run_ocr(self, page: fitz.Page, current_text: str) -> bool:
        """
        Determine if OCR is necessary based on existing text and image coverage.
        """
        word_count = len(current_text.split())
        images = page.get_images(full=False)

        # 1. Fast Path: If there are no images at all, just check if we have enough digital text.
        if not images:
            return word_count < _MIN_DIGITAL_TEXT_WORDS

        # 2. Check Image Coverage: If images exist, calculate how much space they take up.
        page_rect = page.rect
        page_area = page_rect.width * page_rect.height

        if page_area > 0:
            image_info = page.get_image_info()
            image_area = sum(
                (info["bbox"][2] - info["bbox"][0])
                * (info["bbox"][3] - info["bbox"][1])
                for info in image_info
                if "bbox" in info
            )

            # If images cover 10% or more of the page, force OCR to ensure we extract
            # text from charts, diagrams, or embedded screenshots.
            if (image_area / page_area) >= 0.10:
                return True

        # 3. Fallback: Images exist but are tiny (e.g., small logos or bullet point icons).
        # In this case, fall back to checking if we have enough digital text.
        return word_count < _MIN_DIGITAL_TEXT_WORDS

    def _page_to_numpy(self, page: fitz.Page) -> np.ndarray:
        """
        Convert a PyMuPDF page into a NumPy array suitable for OCR.
        """
        page_rect = page.rect
        # Clip 3% off edges to avoid empty scanner margins
        crop_rect = fitz.Rect(
            page_rect.x0 + (page_rect.width * 0.03),
            page_rect.y0 + (page_rect.height * 0.03),
            page_rect.x1 - (page_rect.width * 0.03),
            page_rect.y1 - (page_rect.height * 0.03),
        )

        pix = page.get_pixmap(dpi=_OCR_DPI, clip=crop_rect, alpha=False)

        # Note the .copy() at the end here. It ensures NumPy takes ownership of the memory,
        # preventing C-level segfault crashes if PyMuPDF's garbage collector destroys pix early.
        image_np = (
            np.frombuffer(pix.samples, dtype=np.uint8)
            .reshape(pix.height, pix.width, pix.n)
            .copy()
        )

        return image_np
