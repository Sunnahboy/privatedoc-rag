"use client";

import { useEffect, type MutableRefObject, type RefObject } from "react";

import { clampPage, getPrimaryPageForSpread, getSpreadIndexForPage, spreadContainsPage, type PDFViewMode } from "../readerModel";
import type { PageChangeOrigin, PageTurnState } from "../readerTypes";

const VERTICAL_PAGE_GAP = 32;

interface UseVisiblePageArgs {
  viewMode: PDFViewMode;
  resolvedPageCount: number | null;
  safeCurrentPage: number;
  scrollPageHeight: number;
  scrollTop: number;
  spreadCount: number;
  pageTurnState: PageTurnState | null;
  emitPageChange: (nextPage: number, origin: PageChangeOrigin) => void;
  viewportRef: RefObject<HTMLDivElement | null>;
  lastPageChangeOriginRef: MutableRefObject<PageChangeOrigin>;
  lastViewportPageRef: MutableRefObject<number>;
  pendingProgrammaticPageRef: MutableRefObject<number | null>;
}

export default function useVisiblePage({
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
}: UseVisiblePageArgs) {
  useEffect(() => {
    if (viewMode === "single" || !viewportRef.current || !resolvedPageCount) {
      return;
    }

    if (
      lastPageChangeOriginRef.current === "viewport" &&
      lastViewportPageRef.current === safeCurrentPage
    ) {
      lastPageChangeOriginRef.current = "external";
      return;
    }

    pendingProgrammaticPageRef.current = safeCurrentPage;

    if (viewMode === "scroll") {
      const targetTop = (safeCurrentPage - 1) * (scrollPageHeight + VERTICAL_PAGE_GAP);
      viewportRef.current.scrollTo({ top: targetTop, behavior: "smooth" });
      return;
    }

    const spreadIndex = getSpreadIndexForPage(safeCurrentPage);
    const targetTop = spreadIndex * (scrollPageHeight + VERTICAL_PAGE_GAP);
    viewportRef.current.scrollTo({ top: targetTop, behavior: "smooth" });
  }, [
    lastPageChangeOriginRef,
    lastViewportPageRef,
    pendingProgrammaticPageRef,
    resolvedPageCount,
    safeCurrentPage,
    scrollPageHeight,
    viewMode,
    viewportRef,
  ]);

  useEffect(() => {
    if (pageTurnState) {
      return;
    }

    if (!resolvedPageCount || viewMode === "single") {
      return;
    }

    const itemSize = scrollPageHeight + VERTICAL_PAGE_GAP;
    const anchoredIndex = Math.max(
      0,
      Math.floor((scrollTop + itemSize / 2) / itemSize),
    );

    if (viewMode === "scroll") {
      const nextPage = clampPage(anchoredIndex + 1, resolvedPageCount);

      if (pendingProgrammaticPageRef.current !== null) {
        if (nextPage === pendingProgrammaticPageRef.current) {
          pendingProgrammaticPageRef.current = null;
        }
        return;
      }

      if (nextPage !== safeCurrentPage) {
        emitPageChange(nextPage, "viewport");
      }
      return;
    }

    const spreadIndex = Math.min(Math.max(0, spreadCount - 1), anchoredIndex);
    if (pendingProgrammaticPageRef.current !== null) {
      const pendingSpreadIndex = getSpreadIndexForPage(pendingProgrammaticPageRef.current);
      if (spreadIndex === pendingSpreadIndex) {
        pendingProgrammaticPageRef.current = null;
      }
      return;
    }

    if (!spreadContainsPage(spreadIndex, safeCurrentPage, resolvedPageCount)) {
      const nextPage = getPrimaryPageForSpread(spreadIndex, resolvedPageCount);
      if (nextPage !== safeCurrentPage) {
        emitPageChange(nextPage, "viewport");
      }
    }
  }, [
    emitPageChange,
    pageTurnState,
    pendingProgrammaticPageRef,
    resolvedPageCount,
    safeCurrentPage,
    scrollPageHeight,
    scrollTop,
    spreadCount,
    viewMode,
  ]);
}
