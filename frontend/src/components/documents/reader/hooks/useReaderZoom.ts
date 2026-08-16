"use client";

import { useCallback, useMemo, useState } from "react";

import { clampZoomScale, type PDFViewMode, type ReaderDisplayMode } from "../readerModel";
import type { ZoomMode } from "../readerTypes";

const ZOOM_STEPS = [0.5, 0.67, 0.8, 0.9, 1, 1.1, 1.25, 1.5, 1.75, 2, 2.25, 2.5];
const PAGE_ASPECT_RATIO = 1.414;
const VIEWPORT_PADDING_NORMAL = 48;
const VIEWPORT_PADDING_FOCUS = 20;
const DOUBLE_GUTTER = 24;

function getZoomStep(scale: number, direction: 1 | -1): number {
  if (direction > 0) {
    const nextStep = ZOOM_STEPS.find((step) => step > scale + 0.001);
    return nextStep ?? ZOOM_STEPS[ZOOM_STEPS.length - 1];
  }

  const reversed = [...ZOOM_STEPS].reverse();
  const previousStep = reversed.find((step) => step < scale - 0.001);
  return previousStep ?? ZOOM_STEPS[0];
}

function formatZoom(scale: number): string {
  return `${Math.round(scale * 100)}%`;
}

export default function useReaderZoom({
  viewMode,
  readingMode,
  viewportWidth,
  viewportHeight,
}: {
  viewMode: PDFViewMode;
  readingMode: ReaderDisplayMode;
  viewportWidth: number;
  viewportHeight: number;
}) {
  const [zoomMode, setZoomMode] = useState<ZoomMode>("fit-width");
  const [customZoomScale, setCustomZoomScale] = useState(1);

  const horizontalPadding = readingMode === "focus" ? VIEWPORT_PADDING_FOCUS : VIEWPORT_PADDING_NORMAL;

  const fitWidthSinglePageWidth = useMemo(() => {
    const availableWidth = Math.max(320, viewportWidth - horizontalPadding * 2);
    return Math.min(availableWidth, 980);
  }, [horizontalPadding, viewportWidth]);

  const fitWidthDoublePageWidth = useMemo(() => {
    const availableWidth = Math.max(320, viewportWidth - horizontalPadding * 2 - DOUBLE_GUTTER);
    return Math.min(availableWidth / 2, 680);
  }, [horizontalPadding, viewportWidth]);

  const fitPageSinglePageWidth = useMemo(() => {
    const fitByHeight = Math.max(280, (viewportHeight - 180) / PAGE_ASPECT_RATIO);
    return Math.min(fitWidthSinglePageWidth, fitByHeight);
  }, [fitWidthSinglePageWidth, viewportHeight]);

  const fitPageDoublePageWidth = useMemo(() => {
    const fitByHeight = Math.max(220, (viewportHeight - 180) / PAGE_ASPECT_RATIO);
    return Math.min(fitWidthDoublePageWidth, fitByHeight);
  }, [fitWidthDoublePageWidth, viewportHeight]);

  const basePageWidth = viewMode === "double" ? fitWidthDoublePageWidth : fitWidthSinglePageWidth;
  const fitPageWidth = viewMode === "double" ? fitPageDoublePageWidth : fitPageSinglePageWidth;

  const effectiveZoomScale = useMemo(() => {
    if (zoomMode === "fit-page") {
      return clampZoomScale(fitPageWidth / Math.max(basePageWidth, 1));
    }

    if (zoomMode === "custom") {
      return clampZoomScale(customZoomScale);
    }

    return 1;
  }, [basePageWidth, customZoomScale, fitPageWidth, zoomMode]);

  const pageWidth = Math.max(220, basePageWidth * effectiveZoomScale);
  const zoomLabel = formatZoom(effectiveZoomScale);
  const scrollPageHeight = pageWidth * PAGE_ASPECT_RATIO;

  const setZoomPreset = useCallback((nextMode: Exclude<ZoomMode, "custom">) => {
    setZoomMode(nextMode);
  }, []);

  const zoomByStep = useCallback((direction: 1 | -1) => {
    const nextScale = clampZoomScale(getZoomStep(effectiveZoomScale, direction));
    setZoomMode("custom");
    setCustomZoomScale(nextScale);
  }, [effectiveZoomScale]);

  return {
    zoomMode,
    pageWidth,
    zoomLabel,
    scrollPageHeight,
    setZoomPreset,
    zoomByStep,
    pageAspectRatio: PAGE_ASPECT_RATIO,
    doubleGutter: DOUBLE_GUTTER,
  };
}
