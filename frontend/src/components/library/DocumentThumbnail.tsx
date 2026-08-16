"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

interface DocumentThumbnailProps {
  documentId: string;
  originalFilename: string;
  fileUrl: string;
  forceBackPreview?: boolean;
}

function getExtension(filename: string): string {
  const parts = filename.split(".");
  if (parts.length < 2) {
    return "DOC";
  }
  return parts[parts.length - 1].toUpperCase();
}

export function DocumentThumbnail({
  documentId,
  originalFilename,
  fileUrl,
  forceBackPreview = false,
}: DocumentThumbnailProps) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const [isVisible, setIsVisible] = useState(false);
  const [pageWidth, setPageWidth] = useState(160);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [isHovered, setIsHovered] = useState(false);
  const [hasInteracted, setHasInteracted] = useState(false);

  const isPdf = useMemo(
    () => originalFilename.toLowerCase().endsWith(".pdf"),
    [originalFilename],
  );

  useEffect(() => {
    const host = hostRef.current;
    if (!host || isVisible) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const isIntersecting = entries.some((entry) => entry.isIntersecting);
        if (isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: "240px 0px" },
    );

    observer.observe(host);
    return () => observer.disconnect();
  }, [isVisible]);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) {
      return;
    }

    const resizeObserver = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect.width ?? 0;
      if (width > 0) {
        setPageWidth(Math.max(96, Math.floor(width - 24)));
      }
    });

    resizeObserver.observe(host);
    return () => resizeObserver.disconnect();
  }, []);

  const canShowBackPreview = (numPages ?? 0) > 1;
  const showBackPreview = canShowBackPreview && (isHovered || forceBackPreview);
  const shouldRenderBackPreview = canShowBackPreview && (hasInteracted || forceBackPreview);

  if (!isPdf) {
    return (
      <div
        ref={hostRef}
        className="flex h-full items-center justify-center rounded border border-dashed border-outline-variant/40 bg-white/70 text-on-surface-variant"
      >
        <div className="text-center">
          <p className="text-xs font-semibold tracking-[0.08em]">{getExtension(originalFilename)}</p>
          <p className="mt-1 text-[11px]">Preview unavailable</p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={hostRef}
      className="relative flex h-full items-center justify-center overflow-hidden rounded border border-outline-variant/40 bg-[#fdfcf8]"
      data-thumbnail-id={documentId}
      onMouseEnter={() => {
        setIsHovered(true);
        setHasInteracted(true);
      }}
      onMouseLeave={() => setIsHovered(false)}
    >
      {!isVisible ? (
        <div className="text-xs text-on-surface-variant">Loading preview…</div>
      ) : (
        <Document
          file={fileUrl}
          onLoadSuccess={(result) => {
            setNumPages(result.numPages);
          }}
          loading={<div className="text-xs text-on-surface-variant">Loading preview…</div>}
          error={<div className="px-3 text-center text-xs text-on-surface-variant">PDF preview unavailable</div>}
          className="pointer-events-none"
        >
          <div className="relative flex h-full w-full items-center justify-center">
            <div
              className={`absolute inset-0 flex items-center justify-center transition-opacity duration-200 motion-reduce:transition-none ${
                showBackPreview ? "opacity-0" : "opacity-100"
              }`}
            >
              <Page
                pageNumber={1}
                width={pageWidth}
                renderTextLayer={false}
                renderAnnotationLayer={false}
                loading={<div className="text-xs text-on-surface-variant">Loading page…</div>}
                error={<div className="px-3 text-center text-xs text-on-surface-variant">PDF preview unavailable</div>}
              />
            </div>

            {shouldRenderBackPreview && numPages ? (
              <div
                className={`absolute inset-0 flex items-center justify-center transition-opacity duration-200 motion-reduce:transition-none ${
                  showBackPreview ? "opacity-100" : "opacity-0"
                }`}
              >
                <Page
                  pageNumber={numPages}
                  width={pageWidth}
                  renderTextLayer={false}
                  renderAnnotationLayer={false}
                  loading={<div className="text-xs text-on-surface-variant">Loading page…</div>}
                  error={<div className="px-3 text-center text-xs text-on-surface-variant">PDF preview unavailable</div>}
                />
              </div>
            ) : null}
          </div>
        </Document>
      )}
    </div>
  );
}
