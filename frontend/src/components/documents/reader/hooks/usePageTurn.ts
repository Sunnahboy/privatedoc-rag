"use client";

import { useCallback, useEffect, useRef, useState, type PointerEvent, type TouchEvent } from "react";

import { clampPage, getPrimaryPageForSpread, getSpreadIndexForPage, type PDFViewMode } from "../readerModel";
import type { EdgeDragState, PageChangeOrigin, PageTurnDirection, PageTurnState, SwipeState } from "../readerTypes";

const PAGE_TURN_DURATION_MS = 420;
const SWIPE_MIN_DISTANCE = 56;
const SWIPE_MAX_DURATION_MS = 700;
const EDGE_DRAG_TRIGGER_PX = 56;

interface UsePageTurnArgs {
  viewMode: PDFViewMode;
  safeCurrentPage: number;
  resolvedPageCount: number | null;
  spreadCount: number;
  pageWidth: number;
  emitPageChange: (nextPage: number, origin: PageChangeOrigin) => void;
}

export default function usePageTurn({
  viewMode,
  safeCurrentPage,
  resolvedPageCount,
  spreadCount,
  pageWidth,
  emitPageChange,
}: UsePageTurnArgs) {
  const latestCurrentPageRef = useRef(safeCurrentPage);
  const pageTurnTimeoutRef = useRef<number | null>(null);
  const pageTurnFrameRef = useRef<number | null>(null);
  const isTurningRef = useRef(false);
  const swipeStateRef = useRef<SwipeState | null>(null);
  const edgeDragStateRef = useRef<EdgeDragState | null>(null);
  const suppressNextEdgeClickRef = useRef(false);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
  const [pageTurnState, setPageTurnState] = useState<PageTurnState | null>(null);

  useEffect(() => {
    latestCurrentPageRef.current = safeCurrentPage;
  }, [safeCurrentPage]);

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return;
    }

    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const updatePreference = () => setPrefersReducedMotion(mediaQuery.matches);
    updatePreference();

    mediaQuery.addEventListener("change", updatePreference);
    return () => mediaQuery.removeEventListener("change", updatePreference);
  }, []);

  useEffect(() => {
    return () => {
      if (pageTurnTimeoutRef.current !== null) {
        window.clearTimeout(pageTurnTimeoutRef.current);
      }
      if (pageTurnFrameRef.current !== null) {
        window.cancelAnimationFrame(pageTurnFrameRef.current);
      }
      isTurningRef.current = false;
    };
  }, []);

  const resolveSequentialTargetPage = useCallback((direction: PageTurnDirection): number | null => {
    if (viewMode === "double") {
      const currentSpread = getSpreadIndexForPage(safeCurrentPage);
      const nextSpread = direction === "forward"
        ? Math.min(Math.max(0, spreadCount - 1), currentSpread + 1)
        : Math.max(0, currentSpread - 1);
      const nextPage = getPrimaryPageForSpread(nextSpread, resolvedPageCount);
      return nextPage === safeCurrentPage ? null : nextPage;
    }

    const nextPage = direction === "forward" ? safeCurrentPage + 1 : safeCurrentPage - 1;
    const clamped = clampPage(nextPage, resolvedPageCount);
    return clamped === safeCurrentPage ? null : clamped;
  }, [resolvedPageCount, safeCurrentPage, spreadCount, viewMode]);

  const animateTurnToProgress = useCallback((
    targetProgress: number,
    durationMs: number,
    origin: "toolbar" | "keyboard",
    transition: { fromPage: number; toPage: number },
  ) => {
    if (pageTurnTimeoutRef.current !== null) {
      window.clearTimeout(pageTurnTimeoutRef.current);
      pageTurnTimeoutRef.current = null;
    }
    if (pageTurnFrameRef.current !== null) {
      window.cancelAnimationFrame(pageTurnFrameRef.current);
      pageTurnFrameRef.current = null;
    }

    pageTurnFrameRef.current = window.requestAnimationFrame(() => {
      setPageTurnState((current) => {
        if (!current) {
          return null;
        }

        return {
          ...current,
          phase: "running",
          progress: targetProgress,
          durationMs,
          completes: targetProgress >= 1,
        };
      });
    });

    pageTurnTimeoutRef.current = window.setTimeout(() => {
      if (targetProgress >= 1 && latestCurrentPageRef.current === transition.fromPage) {
        emitPageChange(transition.toPage, origin);
      }
      setPageTurnState(null);
      isTurningRef.current = false;
      pageTurnTimeoutRef.current = null;
    }, durationMs);
  }, [emitPageChange]);

  const startSequentialTurn = useCallback((direction: PageTurnDirection, origin: "toolbar" | "keyboard") => {
    if (pageTurnState || isTurningRef.current) {
      return;
    }

    const targetPage = resolveSequentialTargetPage(direction);
    if (targetPage === null) {
      return;
    }

    if (viewMode === "scroll" || prefersReducedMotion) {
      emitPageChange(targetPage, origin);
      return;
    }

    isTurningRef.current = true;
    setPageTurnState({
      direction,
      fromPage: safeCurrentPage,
      toPage: targetPage,
      phase: "start",
      progress: 0,
      durationMs: PAGE_TURN_DURATION_MS,
      completes: true,
    });
    animateTurnToProgress(1, PAGE_TURN_DURATION_MS, origin, {
      fromPage: safeCurrentPage,
      toPage: targetPage,
    });
  }, [
    animateTurnToProgress,
    emitPageChange,
    pageTurnState,
    prefersReducedMotion,
    resolveSequentialTargetPage,
    safeCurrentPage,
    viewMode,
  ]);

  const goToPrevious = useCallback(() => {
    startSequentialTurn("backward", "toolbar");
  }, [startSequentialTurn]);

  const goToNext = useCallback(() => {
    startSequentialTurn("forward", "toolbar");
  }, [startSequentialTurn]);

  const navigationLocked = pageTurnState !== null;

  const onEdgeClick = useCallback((direction: PageTurnDirection) => {
    if (suppressNextEdgeClickRef.current) {
      suppressNextEdgeClickRef.current = false;
      return;
    }

    startSequentialTurn(direction, "toolbar");
  }, [startSequentialTurn]);

  const onEdgePointerDown = useCallback((direction: PageTurnDirection, event: PointerEvent<HTMLButtonElement>) => {
    if (event.pointerType === "touch" || viewMode === "scroll" || navigationLocked) {
      return;
    }

    const targetPage = resolveSequentialTargetPage(direction);
    if (targetPage === null) {
      return;
    }

    isTurningRef.current = true;
    setPageTurnState({
      direction,
      fromPage: safeCurrentPage,
      toPage: targetPage,
      phase: "dragging",
      progress: 0,
      durationMs: 0,
      completes: false,
    });

    edgeDragStateRef.current = {
      direction,
      pointerId: event.pointerId,
      startX: event.clientX,
      fromPage: safeCurrentPage,
      toPage: targetPage,
      moved: false,
    };

    try {
      event.currentTarget.setPointerCapture(event.pointerId);
    } catch {
      // Pointer capture may not be available in synthetic/unsupported environments.
    }
  }, [navigationLocked, resolveSequentialTargetPage, safeCurrentPage, viewMode]);

  const onEdgePointerMove = useCallback((event: PointerEvent<HTMLButtonElement>) => {
    const dragState = edgeDragStateRef.current;
    if (!dragState || dragState.pointerId !== event.pointerId) {
      return;
    }

    const deltaX = event.clientX - dragState.startX;
    const directionalDistance = dragState.direction === "forward" ? -deltaX : deltaX;
    const nextProgress = Math.max(0, Math.min(1, directionalDistance / Math.max(120, pageWidth * 0.85)));

    setPageTurnState((current) => {
      if (!current || current.phase !== "dragging") {
        return current;
      }

      return {
        ...current,
        progress: nextProgress,
      };
    });

    if (Math.abs(event.clientX - dragState.startX) > 8) {
      dragState.moved = true;
      edgeDragStateRef.current = dragState;
    }
  }, [pageWidth]);

  const onEdgePointerUp = useCallback((event: PointerEvent<HTMLButtonElement>) => {
    const dragState = edgeDragStateRef.current;
    if (!dragState || dragState.pointerId !== event.pointerId) {
      return;
    }

    const deltaX = event.clientX - dragState.startX;
    const directionalDistance = dragState.direction === "forward" ? -deltaX : deltaX;
    const dragProgress = Math.max(0, Math.min(1, directionalDistance / Math.max(120, pageWidth * 0.85)));

    edgeDragStateRef.current = null;
    try {
      if (event.currentTarget.hasPointerCapture(event.pointerId)) {
        event.currentTarget.releasePointerCapture(event.pointerId);
      }
    } catch {
      // Ignore invalid pointer ids from synthetic/ended pointer streams.
    }

    if (directionalDistance >= EDGE_DRAG_TRIGGER_PX) {
      suppressNextEdgeClickRef.current = true;
      const remaining = Math.max(0.16, 1 - dragProgress);
      const duration = Math.max(140, Math.round(PAGE_TURN_DURATION_MS * remaining));
      animateTurnToProgress(1, duration, "toolbar", {
        fromPage: dragState.fromPage,
        toPage: dragState.toPage,
      });
      return;
    }

    const rewindDuration = Math.max(120, Math.round(PAGE_TURN_DURATION_MS * Math.max(0.16, dragProgress)));
    animateTurnToProgress(0, rewindDuration, "toolbar", {
      fromPage: dragState.fromPage,
      toPage: dragState.toPage,
    });

    if (dragState.moved) {
      suppressNextEdgeClickRef.current = true;
    }
  }, [animateTurnToProgress, pageWidth]);

  const onEdgePointerCancel = useCallback((event: PointerEvent<HTMLButtonElement>) => {
    const dragState = edgeDragStateRef.current;
    if (!dragState || dragState.pointerId !== event.pointerId) {
      return;
    }

    edgeDragStateRef.current = null;
    try {
      if (event.currentTarget.hasPointerCapture(event.pointerId)) {
        event.currentTarget.releasePointerCapture(event.pointerId);
      }
    } catch {
      // Ignore invalid pointer ids from synthetic/ended pointer streams.
    }
    animateTurnToProgress(0, 140, "toolbar", {
      fromPage: dragState.fromPage,
      toPage: dragState.toPage,
    });
    suppressNextEdgeClickRef.current = true;
  }, [animateTurnToProgress]);

  const handleTouchStart = useCallback((event: TouchEvent<HTMLDivElement>) => {
    if (viewMode === "scroll" || navigationLocked) {
      swipeStateRef.current = null;
      return;
    }

    if (event.touches.length !== 1) {
      swipeStateRef.current = null;
      return;
    }

    const touch = event.touches[0];
    swipeStateRef.current = {
      startX: touch.clientX,
      startY: touch.clientY,
      startTime: Date.now(),
    };
  }, [navigationLocked, viewMode]);

  const handleTouchEnd = useCallback((event: TouchEvent<HTMLDivElement>) => {
    if (viewMode === "scroll" || navigationLocked) {
      swipeStateRef.current = null;
      return;
    }

    const swipeStart = swipeStateRef.current;
    swipeStateRef.current = null;
    if (!swipeStart || event.changedTouches.length === 0) {
      return;
    }

    const touch = event.changedTouches[0];
    const deltaX = touch.clientX - swipeStart.startX;
    const deltaY = touch.clientY - swipeStart.startY;
    const elapsed = Date.now() - swipeStart.startTime;
    const absX = Math.abs(deltaX);
    const absY = Math.abs(deltaY);

    if (elapsed > SWIPE_MAX_DURATION_MS || absX < SWIPE_MIN_DISTANCE || absX <= absY * 1.2) {
      return;
    }

    if (deltaX < 0) {
      startSequentialTurn("forward", "toolbar");
      return;
    }

    startSequentialTurn("backward", "toolbar");
  }, [navigationLocked, startSequentialTurn, viewMode]);

  return {
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
  };
}
