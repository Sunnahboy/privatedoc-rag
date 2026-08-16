"use client";

import { useEffect } from "react";

import type { ReaderDisplayMode } from "../readerTypes";

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false;
  }

  const tagName = target.tagName.toLowerCase();
  return target.isContentEditable || tagName === "input" || tagName === "textarea" || tagName === "select";
}

interface UseReaderNavigationArgs {
  readingMode: ReaderDisplayMode;
  onReadingModeChange?: (mode: ReaderDisplayMode) => void;
  startSequentialTurn: (direction: "forward" | "backward") => void;
  zoomByStep: (direction: 1 | -1) => void;
}

export default function useReaderNavigation({
  readingMode,
  onReadingModeChange,
  startSequentialTurn,
  zoomByStep,
}: UseReaderNavigationArgs) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (isEditableTarget(event.target)) {
        return;
      }

      if (event.key === "ArrowLeft") {
        event.preventDefault();
        startSequentialTurn("backward");
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        startSequentialTurn("forward");
      } else if ((event.key === "+" || event.key === "=") && !event.metaKey && !event.ctrlKey) {
        event.preventDefault();
        zoomByStep(1);
      } else if (event.key === "-" && !event.metaKey && !event.ctrlKey) {
        event.preventDefault();
        zoomByStep(-1);
      } else if (event.key === "Escape" && readingMode === "focus") {
        onReadingModeChange?.("normal");
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onReadingModeChange, readingMode, startSequentialTurn, zoomByStep]);
}
