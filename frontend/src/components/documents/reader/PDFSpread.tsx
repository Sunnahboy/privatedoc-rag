"use client";

import PDFPageSurface from "./PDFPageSurface";

interface PDFSpreadProps {
  spreadIndex: number;
  leftPage: number | null;
  rightPage: number | null;
  pageWidth: number;
  pageAspectRatio?: number;
  gutter?: number;
}

const DEFAULT_ASPECT_RATIO = 1.414;
const DEFAULT_GUTTER = 24;

export default function PDFSpread({
  spreadIndex,
  leftPage,
  rightPage,
  pageWidth,
  pageAspectRatio = DEFAULT_ASPECT_RATIO,
  gutter = DEFAULT_GUTTER,
}: PDFSpreadProps) {
  const slotHeight = pageWidth * pageAspectRatio;

  const leftSlot = leftPage ? (
    <PDFPageSurface
      pageNumber={leftPage}
      width={pageWidth}
      ariaLabel={`Page ${leftPage}`}
      pageAspectRatio={pageAspectRatio}
    />
  ) : (
    <div aria-hidden="true" className="shrink-0" style={{ width: pageWidth, height: slotHeight }} />
  );

  const rightSlot = rightPage ? (
    <PDFPageSurface
      pageNumber={rightPage}
      width={pageWidth}
      ariaLabel={`Page ${rightPage}`}
      pageAspectRatio={pageAspectRatio}
    />
  ) : (
    <div aria-hidden="true" className="shrink-0" style={{ width: pageWidth, height: slotHeight }} />
  );

  return (
    <div
      id={`pdf-spread-${spreadIndex}`}
      className="flex w-full justify-center"
      style={{ gap: gutter }}
    >
      {leftSlot}
      {rightSlot}
    </div>
  );
}
