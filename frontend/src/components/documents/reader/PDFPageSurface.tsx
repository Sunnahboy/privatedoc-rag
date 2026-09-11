"use client";

import { memo, useMemo } from "react";
import { Page } from "react-pdf";

import { createHighlightTextRenderer, type PageHighlight } from "./highlightText";

interface PDFPageSurfaceProps {
  pageNumber: number;
  width: number;
  ariaLabel: string;
  pageAspectRatio?: number;
  className?: string;
  highlight?: PageHighlight | null;
}

const DEFAULT_ASPECT_RATIO = 1.414;
const SURFACE_BORDER = "border border-outline-variant/30 bg-white";
const SURFACE_SHADOW = "shadow-[0_8px_28px_rgba(15,23,42,0.08)]";

const PDFPageSurface = memo(function PDFPageSurface({
  pageNumber,
  width,
  ariaLabel,
  pageAspectRatio = DEFAULT_ASPECT_RATIO,
  className,
  highlight = null,
}: PDFPageSurfaceProps) {
  const height = width * pageAspectRatio;
  const customTextRenderer = useMemo(
    () => createHighlightTextRenderer(highlight),
    [highlight],
  );

  return (
    <div
      id={`pdf-page-${pageNumber}`}
      data-reader-page={pageNumber}
      className={`relative shrink-0 ${SURFACE_BORDER} ${SURFACE_SHADOW}${className ? ` ${className}` : ""}`}
      style={{ width }}
    >
      <Page
        pageNumber={pageNumber}
        width={width}
        renderTextLayer
        renderAnnotationLayer
        customTextRenderer={customTextRenderer}
        loading={
          <div
            className="flex items-center justify-center text-sm text-on-surface-variant"
            style={{ width, height }}
          >
            Rendering page {pageNumber}…
          </div>
        }
        error={
          <div
            className="flex items-center justify-center px-6 text-center text-sm text-on-surface-variant"
            style={{ width, height }}
          >
            We couldn&apos;t render page {pageNumber}.
          </div>
        }
        aria-label={ariaLabel}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0"
        data-page-overlay={pageNumber}
      />
    </div>
  );
});

export default PDFPageSurface;
