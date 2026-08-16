"use client";

import type { ReactNode } from "react";

import PDFSpread from "./PDFSpread";
import { getSpreadPages } from "./readerModel";
import type { WindowRange } from "./readerTypes";

interface VirtualizedSpreadListProps {
  spreadCount: number;
  totalPages: number;
  pageWidth: number;
  pageAspectRatio: number;
  verticalGap: number;
  gutter: number;
  windowRange: WindowRange;
}

export default function VirtualizedSpreadList({
  spreadCount,
  totalPages,
  pageWidth,
  pageAspectRatio,
  verticalGap,
  gutter,
  windowRange,
}: VirtualizedSpreadListProps) {
  if (!totalPages) {
    return null;
  }

  const spreads: ReactNode[] = [];
  for (let index = windowRange.startIndex; index <= windowRange.endIndex; index += 1) {
    const spread = getSpreadPages(index, totalPages);
    spreads.push(
      <PDFSpread
        key={`spread-${index}`}
        spreadIndex={index}
        leftPage={spread.leftPage}
        rightPage={spread.rightPage}
        pageWidth={pageWidth}
        pageAspectRatio={pageAspectRatio}
        gutter={gutter}
      />,
    );
  }

  const itemSize = pageWidth * pageAspectRatio + verticalGap;
  const topSpacer = windowRange.startIndex * itemSize;
  const renderedCount = Math.max(0, windowRange.endIndex - windowRange.startIndex + 1);
  const bottomSpacer = Math.max(0, spreadCount * itemSize - topSpacer - renderedCount * itemSize);

  return (
    <div className="mx-auto flex w-full flex-col gap-8" style={{ paddingTop: topSpacer, paddingBottom: bottomSpacer }}>
      {spreads}
    </div>
  );
}
