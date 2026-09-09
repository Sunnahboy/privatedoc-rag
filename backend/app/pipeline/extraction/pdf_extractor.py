# app/pipeline/extraction/pdf_extractor.py
import asyncio
import logging
import tempfile
from pathlib import Path
from threading import Lock

import fitz  # PyMuPDF
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    AcceleratorOptions,
    PdfPipelineOptions,
    TableFormerMode,
)
from docling.document_converter import DocumentConverter, PdfFormatOption

from .base import BaseExtractor
from .models import ExtractionResult

logger = logging.getLogger(__name__)


class PDFExtractor(BaseExtractor):
    # Class-level variables to hold Docling in memory
    _converter_instance = None
    _converter_lock = Lock()

    def __init__(self, **kwargs):
        self._initialize_converter()
        self.converter = self.__class__._converter_instance

    @classmethod
    def _initialize_converter(cls):
        # If it's already loaded, exit immediately
        if cls._converter_instance is not None:
            return

        with cls._converter_lock:
            # Double-check inside the lock
            if cls._converter_instance is not None:
                return

            logger.info(
                "Initializing Docling DocumentConverter (CPU Mode) for the first time..."
            )

            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = False
            pipeline_options.do_table_structure = True
            pipeline_options.table_structure_options.mode = TableFormerMode.FAST
            pipeline_options.do_code_enrichment = False
            pipeline_options.do_formula_enrichment = False
            pipeline_options.do_picture_classification = False
            pipeline_options.do_picture_description = False

            pipeline_options.accelerator_options = AcceleratorOptions(
                num_threads=6, device="cuda"
            )

            # Apply options to the converter and cache it at the class level
            cls._converter_instance = DocumentConverter(
                allowed_formats=[InputFormat.PDF],
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                },
            )
            logger.info("Docling loaded successfully!")

    async def extract(self, file_path: Path) -> ExtractionResult:
        if not file_path.exists():
            raise FileNotFoundError(file_path)

        # Run extraction using a temporary sanitized clone
        return await asyncio.to_thread(self._extract_with_sanitized_clone, file_path)

    def _extract_with_sanitized_clone(self, file_path: Path) -> ExtractionResult:
        logger.info(f"[Docling] Processing extraction for: {file_path.name}")

        temp_path: Path | None = None
        source_doc = None

        try:
            with tempfile.NamedTemporaryFile(
                prefix=f"clean_{file_path.stem}_",
                suffix=".pdf",
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)

            source_doc = fitz.open(file_path)
            actual_total_pages = len(source_doc)
            logger.info(
                f"[Docling] Found {actual_total_pages} pages in {file_path.name}. Sanitizing annotations..."
            )

            for page in source_doc:
                annot = page.first_annot
                while annot:
                    next_annot = annot.next
                    annot_type = getattr(annot, "type", None)
                    if isinstance(annot_type, (tuple, list)):
                        annot_type = annot_type[0]

                    if annot_type in {8, 9, 10, 11}:
                        page.delete_annot(annot)
                    annot = next_annot

            source_doc.save(temp_path, garbage=3, deflate=True)

            logger.info(
                f"[Docling] Handing {actual_total_pages} pages over to CPU Layout Models."
            )
            logger.info(
                f"[Docling] NOTE: Docling processes the file as a batch. It will remain silent until all {actual_total_pages} pages are done..."
            )

            result = self.converter.convert(str(temp_path))
            document = result.document

            # Export markdown per-page so downstream cleaning/chunking can
            # keep an accurate page_boundaries list. Exporting the whole
            # document in one call collapses `pages` to a single string,
            # which makes every chunk resolve to page 1.
            page_numbers = sorted(document.pages.keys()) if document.pages else []
            if page_numbers:
                pages = [
                    document.export_to_markdown(page_no=page_no)
                    for page_no in page_numbers
                ]
            else:
                # Fallback for documents where Docling didn't populate
                # per-page metadata (e.g. very small/edge-case PDFs).
                pages = [document.export_to_markdown()]

            total_chars = sum(len(page) for page in pages)
            logger.info(
                f"[Docling] Success! Extracted {total_chars} characters of markdown "
                f"across {len(pages)} page(s)."
            )

            return ExtractionResult(
                pages=pages,
                total_pages=actual_total_pages,
                toc=[],
                metadata={},
            )
        finally:
            if source_doc is not None:
                source_doc.close()

            if temp_path is not None and temp_path.exists():
                temp_path.unlink(missing_ok=True)
