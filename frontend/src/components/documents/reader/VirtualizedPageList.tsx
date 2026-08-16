"use client";

import type { ReactNode } from "react";

import PDFPageSurface from "./PDFPageSurface";
import type { WindowRange } from "./readerTypes";

interface VirtualizedPageListProps {
  pageCount: number;
  pageWidth: number;
  pageAspectRatio: number;
  verticalGap: number;
  windowRange: WindowRange;
}

export default function VirtualizedPageList({
  pageCount,
  pageWidth,
  pageAspectRatio,
  verticalGap,
  windowRange,
}: VirtualizedPageListProps) {
  if (!pageCount) {
    return null;
  }

  const items: ReactNode[] = [];
  for (let index = windowRange.startIndex; index <= windowRange.endIndex; index += 1) {
    const page = index + 1;
    items.push(
      <div key={page} className="flex w-full justify-center">
        <PDFPageSurface
          pageNumber={page}
          width={pageWidth}
          ariaLabel={`Page ${page}`}
          pageAspectRatio={pageAspectRatio}
        />
      </div>,
    );
  }

  const itemSize = pageWidth * pageAspectRatio + verticalGap;
  const topSpacer = windowRange.startIndex * itemSize;
  const renderedCount = Math.max(0, windowRange.endIndex - windowRange.startIndex + 1);
  const bottomSpacer = Math.max(
    0,
    pageCount * itemSize - topSpacer - renderedCount * itemSize,
  );

  return (
    <div className="mx-auto flex w-full flex-col gap-8" style={{ paddingTop: topSpacer, paddingBottom: bottomSpacer }}>
      {items}
    </div>
  );
}
