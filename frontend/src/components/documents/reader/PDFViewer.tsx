"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Document, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

import PageTurnLayer from "./PageTurnLayer";
import PDFPageSurface from "./PDFPageSurface";
import ReaderToolbar from "./ReaderToolbar";
import VirtualizedPageList from "./VirtualizedPageList";
import VirtualizedSpreadList from "./VirtualizedSpreadList";
import { clampPage, getSpreadCount, getSpreadIndexForPage } from "./readerModel";
import type {
  PageChangeOrigin,
  PDFViewMode,
  ReaderChapterContext,
  ReaderDisplayMode,
  WindowRange,
} from "./readerTypes";
import usePDFDocument from "./hooks/usePDFDocument";
import usePageTurn from "./hooks/usePageTurn";
import useReaderNavigation from "./hooks/useReaderNavigation";
import useReaderViewport from "./hooks/useReaderViewport";
import useReaderZoom from "./hooks/useReaderZoom";
import useVisiblePage from "./hooks/useVisiblePage";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

const VIEWPORT_BACKGROUND = "bg-[#F4F1EA]";
const VERTICAL_PAGE_GAP = 32;
const PAGE_OVERSCAN = 3;
const SPREAD_OVERSCAN = 2;
const FOCUS_HUD_HIDE_DELAY_MS = 1800;

function getWindowRange(
  scrollTop: number,
  viewportHeight: number,
  itemSize: number,
  itemCount: number,
  overscan: number,
): WindowRange {
  if (itemCount === 0 || itemSize <= 0) {
    return { startIndex: 0, endIndex: -1 };
  }

  const firstVisibleIndex = Math.floor(scrollTop / itemSize);
  const visibleItemCount = Math.max(1, Math.ceil(viewportHeight / itemSize));

  return {
    startIndex: Math.max(0, firstVisibleIndex - overscan),
    endIndex: Math.min(itemCount - 1, firstVisibleIndex + visibleItemCount + overscan),
  };
}

interface PDFViewerProps {
  fileUrl: string;
  pageNumber: number;
  totalPages?: number | null;
  viewMode?: PDFViewMode;
  readingMode?: ReaderDisplayMode;
  isToolbarOpen?: boolean;
  documentTitle?: string;
  chapterContext?: ReaderChapterContext | null;
  onPageChange?: (page: number) => void;
  onViewModeChange?: (mode: PDFViewMode) => void;
  onReadingModeChange?: (mode: ReaderDisplayMode) => void;
  onToggleToolbar?: () => void;
}

export default function PDFViewer({
  fileUrl,
  pageNumber,
  totalPages,
  viewMode = "single",
  readingMode = "normal",
  isToolbarOpen = true,
  documentTitle,
  chapterContext,
  onPageChange,
  onViewModeChange,
  onReadingModeChange,
  onToggleToolbar,
}: PDFViewerProps) {
  const shellRef = useRef<HTMLDivElement>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  const lastViewportPageRef = useRef(pageNumber);
  const lastPageChangeOriginRef = useRef<PageChangeOrigin>("external");
  const pendingProgrammaticPageRef = useRef<number | null>(null);
  const focusHudTimeoutRef = useRef<number | null>(null);
  const [showFocusHud, setShowFocusHud] = useState(readingMode !== "focus");

  const {
    resolvedPageCount,
    loadState,
    loadError,
    reloadKey,
    handleRetry,
    onDocumentLoadSuccess,
    onDocumentLoadError,
    formatDocumentError,
  } = usePDFDocument(totalPages);

  const safeCurrentPage = clampPage(pageNumber, resolvedPageCount);
  const { viewportWidth, viewportHeight, scrollTop } = useReaderViewport({ shellRef, viewportRef });
  const {
    zoomMode,
    pageWidth,
    zoomLabel,
    scrollPageHeight,
    setZoomPreset,
    zoomByStep,
    pageAspectRatio,
    doubleGutter,
  } = useReaderZoom({
    viewMode,
    readingMode,
    viewportWidth,
    viewportHeight,
  });

  const spreadCount = getSpreadCount(resolvedPageCount);
  const scrollWindow = useMemo(
    () => getWindowRange(
      scrollTop,
      viewportHeight,
      scrollPageHeight + VERTICAL_PAGE_GAP,
      resolvedPageCount ?? 0,
      PAGE_OVERSCAN,
    ),
    [resolvedPageCount, scrollPageHeight, scrollTop, viewportHeight],
  );
  const spreadWindow = useMemo(
    () => getWindowRange(
      scrollTop,
      viewportHeight,
      scrollPageHeight + VERTICAL_PAGE_GAP,
      spreadCount,
      SPREAD_OVERSCAN,
    ),
    [scrollPageHeight, scrollTop, spreadCount, viewportHeight],
  );

  const emitPageChange = useCallback(
    (nextPage: number, origin: PageChangeOrigin) => {
      const clamped = clampPage(nextPage, resolvedPageCount);
      lastViewportPageRef.current = clamped;
      lastPageChangeOriginRef.current = origin;

      if (clamped !== safeCurrentPage) {
        onPageChange?.(clamped);
      }
    },
    [onPageChange, resolvedPageCount, safeCurrentPage],
  );

  const {
    pageTurnState,
    navigationLocked,
    startSequentialTurn,
    goToPrevious,
    goToNext,
    onEdgeClick,
    onEdgePointerDown,
    onEdgePointerMove,
    onEdgePointerUp,
    onEdgePointerCancel,
    handleTouchStart,
    handleTouchEnd,
  } = usePageTurn({
    viewMode,
    safeCurrentPage,
    resolvedPageCount,
    spreadCount,
    pageWidth,
    emitPageChange,
  });

  useVisiblePage({
    viewMode,
    resolvedPageCount,
    safeCurrentPage,
    scrollPageHeight,
    scrollTop,
    spreadCount,
    pageTurnState,
    emitPageChange,
    viewportRef,
    lastPageChangeOriginRef,
    lastViewportPageRef,
    pendingProgrammaticPageRef,
  });

  const clearFocusHudTimeout = useCallback(() => {
    if (focusHudTimeoutRef.current !== null) {
      window.clearTimeout(focusHudTimeoutRef.current);
      focusHudTimeoutRef.current = null;
    }
  }, []);

  const revealFocusHud = useCallback(() => {
    if (readingMode !== "focus") {
      return;
    }

    setShowFocusHud(true);
    clearFocusHudTimeout();
    focusHudTimeoutRef.current = window.setTimeout(() => {
      setShowFocusHud(false);
      focusHudTimeoutRef.current = null;
    }, FOCUS_HUD_HIDE_DELAY_MS);
  }, [clearFocusHudTimeout, readingMode]);

  useEffect(() => {
    if (readingMode !== "focus") {
      clearFocusHudTimeout();
      return;
    }

    const timerId = window.setTimeout(() => {
      revealFocusHud();
    }, 0);

    return () => window.clearTimeout(timerId);
  }, [clearFocusHudTimeout, readingMode, revealFocusHud]);

  useReaderNavigation({
    readingMode,
    onReadingModeChange,
    startSequentialTurn: (direction) => startSequentialTurn(direction, "keyboard"),
    zoomByStep,
  });

  useEffect(() => {
    return () => {
      clearFocusHudTimeout();
    };
  }, [clearFocusHudTimeout]);

  const pageCounterLabel = resolvedPageCount
    ? `Page ${safeCurrentPage} of ${resolvedPageCount}`
    : `Page ${safeCurrentPage}`;
  const currentSpreadIndex = getSpreadIndexForPage(safeCurrentPage);
  const isAtFirstPosition = viewMode === "double" ? currentSpreadIndex <= 0 : safeCurrentPage <= 1;
  const isAtLastPosition = viewMode === "double"
    ? currentSpreadIndex >= Math.max(0, spreadCount - 1)
    : resolvedPageCount !== null && safeCurrentPage >= resolvedPageCount;
  const sequentialTurningEnabled = viewMode === "single" || viewMode === "double";
  const activePageTurnState = pageTurnState && pageTurnState.fromPage === safeCurrentPage
    ? pageTurnState
    : null;

  return (
    <section className={`relative flex h-full min-h-0 flex-col ${VIEWPORT_BACKGROUND} text-on-surface`} aria-label="Document reader">
      {readingMode !== "focus" && (
        <ReaderToolbar
          isOpen={isToolbarOpen}
          pageCounterLabel={pageCounterLabel}
          chapterContext={chapterContext}
          documentTitle={documentTitle}
          viewMode={viewMode}
          readingMode={readingMode}
          navigationLocked={navigationLocked}
          isAtFirstPosition={isAtFirstPosition}
          isAtLastPosition={isAtLastPosition}
          zoomLabel={zoomLabel}
          zoomMode={zoomMode}
          onPrevious={goToPrevious}
          onNext={goToNext}
          onViewModeChange={(mode) => onViewModeChange?.(mode)}
          onZoomOut={() => zoomByStep(-1)}
          onZoomIn={() => zoomByStep(1)}
          onFitPage={() => setZoomPreset("fit-page")}
          onFitWidth={() => setZoomPreset("fit-width")}
          onReadingModeChange={(mode) => onReadingModeChange?.(mode)}
          onToggleOpen={onToggleToolbar ?? (() => undefined)}
        />
      )}

      {readingMode === "focus" && (
        <div
          className={`pointer-events-none absolute inset-x-0 top-0 z-20 transition-opacity duration-300 ${
            showFocusHud ? "opacity-100" : "opacity-0"
          }`}
        >
          <div className="mx-3 mt-3 flex items-center justify-between gap-2 rounded-md border border-outline-variant/30 bg-[#F7F5EF]/95 px-3 py-2 backdrop-blur-[1px] md:mx-6">
            <button
              type="button"
              onClick={() => onReadingModeChange?.("normal")}
              className="pointer-events-auto inline-flex h-8 items-center gap-1 rounded-md border border-outline-variant/30 bg-white px-2.5 text-xs font-medium text-on-surface transition-colors hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
            >
              <span className="material-symbols-outlined text-[16px]">arrow_back</span>
              Exit focus
            </button>

            <div className="pointer-events-auto flex items-center gap-1 rounded-md border border-outline-variant/30 bg-white p-1">
              <button
                type="button"
                aria-label="Previous page"
                onClick={goToPrevious}
                disabled={isAtFirstPosition || navigationLocked}
                className="inline-flex h-9 items-center justify-center rounded-md border border-outline-variant/30 bg-white px-3 text-sm text-on-surface transition-colors hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <span className="material-symbols-outlined text-[18px]">chevron_left</span>
              </button>
              <button
                type="button"
                aria-label="Next page"
                onClick={goToNext}
                disabled={isAtLastPosition || navigationLocked}
                className="inline-flex h-9 items-center justify-center rounded-md border border-outline-variant/30 bg-white px-3 text-sm text-on-surface transition-colors hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <span className="material-symbols-outlined text-[18px]">chevron_right</span>
              </button>
            </div>

            <p className="pointer-events-none text-xs tabular-nums text-on-surface-variant md:text-sm">{pageCounterLabel}</p>
          </div>
        </div>
      )}

      <div ref={shellRef} className="min-h-0 flex-1">
        <div
          ref={viewportRef}
          className={`relative h-full overflow-y-auto px-4 py-6 md:px-6 ${readingMode === "focus" ? "pt-6 md:pt-7" : ""}`}
          onTouchStart={handleTouchStart}
          onTouchEnd={handleTouchEnd}
          onMouseMove={revealFocusHud}
          onPointerDown={revealFocusHud}
          onWheel={revealFocusHud}
          tabIndex={0}
          aria-label="Reader viewport"
        >
          <Document
            key={`${fileUrl}-${reloadKey}`}
            file={fileUrl}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={onDocumentLoadError}
            loading={
              <div className="flex min-h-[60vh] items-center justify-center">
                <div className="max-w-sm text-center">
                  <p className="text-base font-medium text-on-surface">Opening book…</p>
                  <p className="mt-2 text-sm text-on-surface-variant">
                    Preparing pages, text, and search layers.
                  </p>
                </div>
              </div>
            }
            error={
              <div className="flex min-h-[60vh] items-center justify-center">
                <div className="max-w-md rounded-xl border border-outline-variant/30 bg-white px-6 py-5 text-center shadow-sm">
                  <p className="text-base font-medium text-on-surface">Unable to open this document.</p>
                  <p className="mt-2 text-sm text-on-surface-variant">
                    {formatDocumentError(loadError)}
                  </p>
                  <button
                    type="button"
                    onClick={handleRetry}
                    className="mt-4 inline-flex items-center rounded-md border border-outline-variant/30 px-4 py-2 text-sm font-medium text-on-surface transition-colors hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
                  >
                    Try again
                  </button>
                </div>
              </div>
            }
            noData={
              <div className="flex min-h-[60vh] items-center justify-center">
                <div className="max-w-md rounded-xl border border-outline-variant/30 bg-white px-6 py-5 text-center shadow-sm">
                  <p className="text-base font-medium text-on-surface">No document is available.</p>
                  <p className="mt-2 text-sm text-on-surface-variant">
                    Check the file source and try opening the book again.
                  </p>
                </div>
              </div>
            }
            className="mx-auto flex w-full justify-center"
          >
            {viewMode === "single" && activePageTurnState && resolvedPageCount ? (
              <PageTurnLayer
                viewMode="single"
                pageTurnState={activePageTurnState}
                totalPages={resolvedPageCount}
                pageWidth={pageWidth}
                pageAspectRatio={pageAspectRatio}
                gutter={doubleGutter}
              />
            ) : null}

            {viewMode === "single" && !activePageTurnState && (
              <div className="flex w-full justify-center">
                <PDFPageSurface
                  pageNumber={safeCurrentPage}
                  width={pageWidth}
                  ariaLabel={`Page ${safeCurrentPage}`}
                  pageAspectRatio={pageAspectRatio}
                />
              </div>
            )}

            {viewMode === "double" && loadState !== "error" && activePageTurnState && resolvedPageCount ? (
              <PageTurnLayer
                viewMode="double"
                pageTurnState={activePageTurnState}
                totalPages={resolvedPageCount}
                pageWidth={pageWidth}
                pageAspectRatio={pageAspectRatio}
                gutter={doubleGutter}
              />
            ) : null}

            {viewMode === "double" && loadState !== "error" && !activePageTurnState && resolvedPageCount ? (
              <VirtualizedSpreadList
                spreadCount={spreadCount}
                totalPages={resolvedPageCount}
                pageWidth={pageWidth}
                pageAspectRatio={pageAspectRatio}
                verticalGap={VERTICAL_PAGE_GAP}
                gutter={doubleGutter}
                windowRange={spreadWindow}
              />
            ) : null}

            {viewMode === "scroll" && loadState !== "error" && resolvedPageCount ? (
              <VirtualizedPageList
                pageCount={resolvedPageCount}
                pageWidth={pageWidth}
                pageAspectRatio={pageAspectRatio}
                verticalGap={VERTICAL_PAGE_GAP}
                windowRange={scrollWindow}
              />
            ) : null}
          </Document>

          {sequentialTurningEnabled && loadState !== "error" && (
            <>
              <button
                type="button"
                aria-label="Previous page edge control"
                onClick={() => onEdgeClick("backward")}
                onPointerDown={(event) => onEdgePointerDown("backward", event)}
                onPointerMove={onEdgePointerMove}
                onPointerUp={onEdgePointerUp}
                onPointerCancel={onEdgePointerCancel}
                disabled={isAtFirstPosition || navigationLocked}
                className={`pointer-events-auto absolute bottom-6 left-0 top-6 z-5 hidden w-12 items-center justify-center rounded-r-md text-on-surface-variant transition-all duration-200 hover:bg-[#00000008] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 disabled:opacity-30 md:flex md:w-16 ${
                  readingMode === "focus" && !showFocusHud ? "opacity-0" : "opacity-100"
                }`}
              >
                <span className="material-symbols-outlined text-[18px]">chevron_left</span>
              </button>
              <button
                type="button"
                aria-label="Next page edge control"
                onClick={() => onEdgeClick("forward")}
                onPointerDown={(event) => onEdgePointerDown("forward", event)}
                onPointerMove={onEdgePointerMove}
                onPointerUp={onEdgePointerUp}
                onPointerCancel={onEdgePointerCancel}
                disabled={isAtLastPosition || navigationLocked}
                className={`pointer-events-auto absolute bottom-6 right-0 top-6 z-5 hidden w-12 items-center justify-center rounded-l-md text-on-surface-variant transition-all duration-200 hover:bg-[#00000008] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 disabled:opacity-30 md:flex md:w-16 ${
                  readingMode === "focus" && !showFocusHud ? "opacity-0" : "opacity-100"
                }`}
              >
                <span className="material-symbols-outlined text-[18px]">chevron_right</span>
              </button>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
