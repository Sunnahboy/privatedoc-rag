import asyncio
import logging
import os
import site
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock, Semaphore

# --- Windows CUDA DLL Injection for ONNX Runtime ---
# Fast, direct path registration instead of expensive filesystem globbing
if sys.platform == "win32":
    for site_path in site.getsitepackages():
        sp = Path(site_path)

        # Explicit CUDA DLL directories created by PyTorch & NVIDIA wheels
        candidate_dirs = [
            sp / "torch" / "lib",
            sp / "nvidia" / "cublas" / "bin",
            sp / "nvidia" / "cudnn" / "bin",
            sp / "nvidia" / "cuda_nvrtc" / "bin",
            sp / "nvidia" / "cuda_runtime" / "bin",
        ]

        for dll_dir in candidate_dirs:
            if dll_dir.exists():
                os.environ["PATH"] = str(dll_dir) + os.path.pathsep + os.environ["PATH"]
                try:
                    os.add_dll_directory(str(dll_dir))
                except Exception:
                    pass

import fitz
import numpy as np
import onnxruntime as ort
from rapidocr_onnxruntime import RapidOCR

from .base import BaseExtractor
from .models import ExtractionResult

logger = logging.getLogger(__name__)

_MIN_DIGITAL_TEXT_WORDS = 15
_OCR_DPI = int(os.environ.get("PDF_OCR_DPI", "72"))

_OCR_ENGINE: RapidOCR | None = None
_ENGINE_LOCK = Lock()
_OCR_SEMAPHORE: Semaphore | None = None


def get_ocr_engine() -> RapidOCR:
    """Lazily initialize RapidOCR on GPU."""
    global _OCR_ENGINE, _OCR_SEMAPHORE

    if _OCR_ENGINE is None:
        with _ENGINE_LOCK:
            if _OCR_ENGINE is None:
                has_cuda = "CUDAExecutionProvider" in ort.get_available_providers()

                logger.info("Initializing RapidOCR engine (has_cuda=%s)...", has_cuda)
                print(f"[OCR] Initializing RapidOCR engine (GPU={has_cuda})...")

                if has_cuda:
                    _OCR_ENGINE = RapidOCR(
                        det_use_cuda=True,
                        rec_use_cuda=True,
                        cls_use_cuda=True,
                    )
                else:
                    _OCR_ENGINE = RapidOCR()

                max_concurrent = int(
                    os.environ.get("PDF_OCR_MAX_CONCURRENT", "4" if has_cuda else "2")
                )
                _OCR_SEMAPHORE = Semaphore(max_concurrent)

                logger.info("RapidOCR ready.")
                print(
                    f"[OCR] RapidOCR engine ready (Max concurrent: {max_concurrent}, DPI: {_OCR_DPI})."
                )

    return _OCR_ENGINE


def _chunk_ranges(total: int, num_chunks: int) -> list[range]:
    """Split [0, total) into num_chunks contiguous, roughly-equal ranges."""
    if total == 0 or num_chunks == 0:
        return []

    base, remainder = divmod(total, num_chunks)
    ranges = []
    start = 0

    for i in range(num_chunks):
        size = base + (1 if i < remainder else 0)
        if size == 0:
            continue
        ranges.append(range(start, start + size))
        start += size

    return ranges


class PDFExtractor(BaseExtractor):
    """
    PDF extraction strategy using native text with RapidOCR GPU fallback.
    """

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

            max_workers = min(total_pages, 4)
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
                    text = self._process_single_page(document, page_number, worker_id)
                    results.append(text)
                    print(
                        f"[worker {worker_id}] page {page_number + 1} done "
                        f"in {time.perf_counter() - page_start:.2f}s "
                        f"({len(text)} chars)"
                    )
        except Exception:
            logger.exception(
                "Failed processing page range %d-%d",
                page_range.start,
                page_range.stop - 1,
            )
            print(
                f"[worker {worker_id}] FAILED processing pages "
                f"{page_range.start + 1}-{page_range.stop}"
            )
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
        """Extract one page using native text with RapidOCR GPU fallback."""

        try:
            page = document.load_page(page_number)
            text = page.get_text().strip()
            word_count = len(text.split())

            # Fast Path 1: Native digital text is sufficient
            if word_count >= _MIN_DIGITAL_TEXT_WORDS:
                return text

            # Fast Path 2: Check image coverage on page before doing OCR
            images = page.get_images(full=False)
            if not images:
                return text

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
                if (image_area / page_area) < 0.10 and text:
                    return text

            # Clip 3% off edges to avoid empty scanner margins
            crop_rect = fitz.Rect(
                page_rect.x0 + (page_rect.width * 0.03),
                page_rect.y0 + (page_rect.height * 0.03),
                page_rect.x1 - (page_rect.width * 0.03),
                page_rect.y1 - (page_rect.height * 0.03),
            )

            pix = page.get_pixmap(
                dpi=_OCR_DPI,
                clip=crop_rect,
                alpha=False,
            )

            image_np = np.frombuffer(
                pix.samples,
                dtype=np.uint8,
            ).reshape(
                pix.height,
                pix.width,
                pix.n,
            )

            # Fast Path 3: Skip blank/pure white pages
            if image_np.size > 0 and np.mean(image_np) > 252:
                return text

            engine = get_ocr_engine()

            assert _OCR_SEMAPHORE is not None
            with _OCR_SEMAPHORE:
                ocr_start = time.perf_counter()
                ocr_result, _ = engine(image_np)
                ocr_time = time.perf_counter() - ocr_start

            if ocr_result:
                ocr_text = "\n".join(line[1] for line in ocr_result if line[1]).strip()
            else:
                ocr_text = ""

            logger.debug(
                "Page %d RapidOCR completed in %.2fs",
                page_number + 1,
                ocr_time,
            )

            return ocr_text or text

        except Exception:
            logger.exception(
                "Failed processing page %d",
                page_number + 1,
            )
            return ""
