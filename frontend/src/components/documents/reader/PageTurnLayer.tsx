"use client";

import PDFPageSurface from "./PDFPageSurface";
import PDFSpread from "./PDFSpread";
import { getSpreadIndexForPage, getSpreadPages } from "./readerModel";
import type { PDFViewMode, PageTurnState } from "./readerTypes";

interface PageTurnLayerProps {
  viewMode: PDFViewMode;
  pageTurnState: PageTurnState;
  totalPages: number;
  pageWidth: number;
  pageAspectRatio: number;
  gutter: number;
}

export default function PageTurnLayer({
  viewMode,
  pageTurnState,
  totalPages,
  pageWidth,
  pageAspectRatio,
  gutter,
}: PageTurnLayerProps) {
  if (viewMode === "single") {
    const turnDegrees = (pageTurnState.direction === "forward" ? -165 : 165) * pageTurnState.progress;
    const fromTransform = `rotateY(${turnDegrees}deg)`;
    const fromOrigin = pageTurnState.direction === "forward" ? "right center" : "left center";

    return (
      <div className="flex w-full justify-center">
        <div
          className="relative"
          style={{
            width: pageWidth,
            height: pageWidth * pageAspectRatio,
            perspective: "1800px",
          }}
        >
          <div className="absolute inset-0">
            <PDFPageSurface
              pageNumber={pageTurnState.toPage}
              width={pageWidth}
              ariaLabel={`Page ${pageTurnState.toPage}`}
              pageAspectRatio={pageAspectRatio}
            />
          </div>
          <div
            className="absolute inset-0 will-change-transform"
            style={{
              transform: fromTransform,
              transformOrigin: fromOrigin,
              backfaceVisibility: "hidden",
              transition: pageTurnState.phase === "running"
                ? `transform ${pageTurnState.durationMs}ms cubic-bezier(0.23, 0.86, 0.32, 1)`
                : "none",
            }}
          >
            <PDFPageSurface
              pageNumber={pageTurnState.fromPage}
              width={pageWidth}
              ariaLabel={`Page ${pageTurnState.fromPage}`}
              pageAspectRatio={pageAspectRatio}
            />
            <div
              aria-hidden="true"
              className="pointer-events-none absolute inset-0"
              style={{
                background: "linear-gradient(to left, rgba(15,23,42,0.20), rgba(15,23,42,0.02) 38%, transparent 60%)",
                opacity: pageTurnState.progress,
                transition: pageTurnState.phase === "running"
                  ? `opacity ${pageTurnState.durationMs}ms ease`
                  : "none",
              }}
            />
          </div>
        </div>
      </div>
    );
  }

  const fromSpreadIndex = getSpreadIndexForPage(pageTurnState.fromPage);
  const toSpreadIndex = getSpreadIndexForPage(pageTurnState.toPage);
  const fromSpread = getSpreadPages(fromSpreadIndex, totalPages);
  const toSpread = getSpreadPages(toSpreadIndex, totalPages);
  const turningPageNumber = pageTurnState.direction === "forward" ? fromSpread.rightPage : fromSpread.leftPage;
  const anchorPageNumber = pageTurnState.direction === "forward" ? fromSpread.leftPage : fromSpread.rightPage;

  const totalSpreadWidth = pageWidth * 2 + gutter;
  const turnTranslate = pageTurnState.direction === "forward"
    ? -(pageWidth + gutter / 2)
    : pageWidth + gutter / 2;
  const turnDegrees = (pageTurnState.direction === "forward" ? -165 : 165) * pageTurnState.progress;
  const turnX = turnTranslate * pageTurnState.progress;
  const turnTransform = `translateX(${turnX}px) rotateY(${turnDegrees}deg)`;
  const turningSlotStyle = pageTurnState.direction === "forward"
    ? { right: 0, transformOrigin: "right center" as const }
    : { left: 0, transformOrigin: "left center" as const };
  const anchorSlotStyle = pageTurnState.direction === "forward"
    ? { left: 0 }
    : { right: 0 };
  const anchorOpacity = Math.max(0, 1 - pageTurnState.progress * 1.35);

  return (
    <div className="flex w-full justify-center">
      <div
        className="relative"
        style={{
          width: totalSpreadWidth,
          height: pageWidth * pageAspectRatio,
          perspective: "2000px",
        }}
      >
        <div className="absolute inset-0">
          <PDFSpread
            spreadIndex={toSpreadIndex}
            leftPage={toSpread.leftPage}
            rightPage={toSpread.rightPage}
            pageWidth={pageWidth}
            pageAspectRatio={pageAspectRatio}
            gutter={gutter}
          />
        </div>

        {anchorPageNumber ? (
          <div
            className="absolute top-0"
            style={{
              width: pageWidth,
              ...anchorSlotStyle,
              opacity: anchorOpacity,
              transition: pageTurnState.phase === "running"
                ? `opacity ${Math.max(180, pageTurnState.durationMs - 90)}ms ease-out`
                : "none",
            }}
          >
            <PDFPageSurface
              pageNumber={anchorPageNumber}
              width={pageWidth}
              ariaLabel={`Page ${anchorPageNumber}`}
              pageAspectRatio={pageAspectRatio}
            />
          </div>
        ) : null}

        {turningPageNumber ? (
          <div
            className="absolute top-0 will-change-transform"
            style={{
              width: pageWidth,
              ...turningSlotStyle,
              transform: turnTransform,
              backfaceVisibility: "hidden",
              transition: pageTurnState.phase === "running"
                ? `transform ${pageTurnState.durationMs}ms cubic-bezier(0.23, 0.86, 0.32, 1)`
                : "none",
            }}
          >
            <PDFPageSurface
              pageNumber={turningPageNumber}
              width={pageWidth}
              ariaLabel={`Page ${turningPageNumber}`}
              pageAspectRatio={pageAspectRatio}
            />
            <div
              aria-hidden="true"
              className="pointer-events-none absolute inset-0"
              style={{
                background: pageTurnState.direction === "forward"
                  ? "linear-gradient(to left, rgba(15,23,42,0.24), rgba(15,23,42,0.03) 42%, transparent 70%)"
                  : "linear-gradient(to right, rgba(15,23,42,0.24), rgba(15,23,42,0.03) 42%, transparent 70%)",
                opacity: pageTurnState.progress,
                transition: pageTurnState.phase === "running"
                  ? `opacity ${pageTurnState.durationMs}ms ease`
                  : "none",
              }}
            />
          </div>
        ) : null}

        <div
          aria-hidden="true"
          className="pointer-events-none absolute bottom-0 left-1/2 top-0 w-px"
          style={{
            background: "linear-gradient(to bottom, rgba(18,28,42,0.10), rgba(18,28,42,0.24), rgba(18,28,42,0.10))",
            transform: "translateX(-0.5px)",
          }}
        />
      </div>
    </div>
  );
}
