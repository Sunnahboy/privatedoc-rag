import logging
import os
import site
import sys
import time
from pathlib import Path
from threading import Lock, Semaphore

import numpy as np
import onnxruntime as ort
from app.config import settings
from rapidocr_onnxruntime import RapidOCR

from .base import BaseOCR

logger = logging.getLogger(__name__)


def setup_cuda_paths() -> None:
    """
    Registers site-packages CUDA libraries for ONNX Runtime.
    Handles Windows DLL injection and Linux LD_LIBRARY_PATH augmentation.
    """
    # Apple/macOS doesn't use CUDA, skip entirely
    if sys.platform == "darwin":
        return

    site_packages = site.getsitepackages()

    for site_path in site_packages:
        sp = Path(site_path)

        # Standard directories created by PyTorch and NVIDIA pip packages
        candidate_dirs = [
            sp / "torch" / "lib",
            sp / "nvidia" / "cublas" / "lib",
            sp / "nvidia" / "cudnn" / "lib",
            sp / "nvidia" / "cuda_nvrtc" / "lib",
            sp / "nvidia" / "cuda_runtime" / "lib",
            sp / "nvidia" / "cublas" / "bin",
            sp / "nvidia" / "cudnn" / "bin",
            sp / "nvidia" / "cuda_nvrtc" / "bin",
            sp / "nvidia" / "cuda_runtime" / "bin",
        ]

        for dll_dir in candidate_dirs:
            if not dll_dir.exists():
                continue

            if sys.platform == "win32":
                # Windows requires both PATH and add_dll_directory
                os.environ["PATH"] = (
                    str(dll_dir) + os.path.pathsep + os.environ.get("PATH", "")
                )
                try:
                    os.add_dll_directory(str(dll_dir))
                except OSError as e:
                    logger.warning("Failed to add DLL dir %s: %s", dll_dir, e)

            elif sys.platform == "linux":
                # Safely append to LD_LIBRARY_PATH instead of blind CDLL loading
                current_ld = os.environ.get("LD_LIBRARY_PATH", "")
                if str(dll_dir) not in current_ld:
                    os.environ["LD_LIBRARY_PATH"] = (
                        str(dll_dir) + os.path.pathsep + current_ld
                    )


# Execute helper once when the OCR Module is loaded
setup_cuda_paths()


class RapidOCREngine(BaseOCR):
    """RapidOCR implementation of the BaseOCR interface.
    Handles lazy initialization, GPU fallback, and concurrency limits."""

    _engine_instance: RapidOCR | None = None
    _engine_lock = Lock()
    _semaphore: Semaphore | None = None

    def __init__(self):
        # lazy initialization is deferred to the first extract() call

        ...

    @classmethod
    def _initialize_engine(cls) -> None:
        if cls._engine_instance is not None:
            return

        with cls._engine_lock:
            if cls._engine_instance is None:
                has_cuda = "CUDAExecutionProvider" in ort.get_available_providers()
                logger.info("Initializing RapidOCR engine (has_cuda=%s)...", has_cuda)

                if has_cuda:
                    cls._engine_instance = RapidOCR(
                        det_use_cuda=True,
                        rec_use_cuda=True,
                        cls_use_cuda=True,
                    )
                else:
                    cls._engine_instance = RapidOCR()

                max_concurrent = settings.pdf_ocr_max_concurrent
                cls._semaphore = Semaphore(max_concurrent)

                logger.info("RapidOCR ready. Max concurrent: %d", max_concurrent)

    def extract(self, image: np.ndarray) -> str:
        """
        Extract text from a NumPy array image using RapidOCR.
        """
        if image.size == 0:
            return ""

        self._initialize_engine()

        assert self._engine_instance is not None
        assert self._semaphore is not None

        with self._semaphore:
            ocr_start = time.perf_counter()
            try:
                ocr_result, _ = self._engine_instance(image)
                ocr_time = time.perf_counter() - ocr_start
                logger.debug("RapidOCR completed in %.2fs", ocr_time)

                if ocr_result:
                    return "\n".join(line[1] for line in ocr_result if line[1]).strip()
                return ""
            except Exception:
                logger.exception(
                    "RapidOCR extraction failed on image shape %s", image.shape
                )
                return ""
