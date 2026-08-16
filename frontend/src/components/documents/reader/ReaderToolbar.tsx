"use client";

import type { ReactNode } from "react";

import type { PDFViewMode, ReaderDisplayMode, ReaderChapterContext } from "./readerTypes";

interface ReaderToolbarProps {
  isOpen: boolean;
  pageCounterLabel: string;
  chapterContext: ReaderChapterContext | null | undefined;
  documentTitle?: string;
  viewMode: PDFViewMode;
  readingMode: ReaderDisplayMode;
  navigationLocked: boolean;
  isAtFirstPosition: boolean;
  isAtLastPosition: boolean;
  zoomLabel: string;
  zoomMode: "fit-width" | "fit-page" | "custom";
  onPrevious: () => void;
  onNext: () => void;
  onViewModeChange: (mode: PDFViewMode) => void;
  onZoomOut: () => void;
  onZoomIn: () => void;
  onFitPage: () => void;
  onFitWidth: () => void;
  onReadingModeChange: (mode: ReaderDisplayMode) => void;
  onToggleOpen: () => void;
}

function ToolbarButton({
  children,
  ariaLabel,
  onClick,
  disabled,
  active,
}: {
  children: ReactNode;
  ariaLabel: string;
  onClick: () => void;
  disabled?: boolean;
  active?: boolean;
}) {
  return (
    <button
      type="button"
      aria-label={ariaLabel}
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex h-9 items-center justify-center rounded-md border px-3 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 disabled:cursor-not-allowed disabled:opacity-50 ${
        active
          ? "border-primary/30 bg-primary/10 text-primary"
          : "border-outline-variant/30 bg-white text-on-surface hover:bg-surface"
      }`}
    >
      {children}
    </button>
  );
}

export default function ReaderToolbar({
  isOpen,
  pageCounterLabel,
  chapterContext,
  documentTitle,
  viewMode,
  readingMode,
  navigationLocked,
  isAtFirstPosition,
  isAtLastPosition,
  zoomLabel,
  zoomMode,
  onPrevious,
  onNext,
  onViewModeChange,
  onZoomOut,
  onZoomIn,
  onFitPage,
  onFitWidth,
  onReadingModeChange,
  onToggleOpen,
}: ReaderToolbarProps) {
  const sequentialTurningEnabled = viewMode === "single" || viewMode === "double";
  const summaryText = chapterContext
    ? `${chapterContext.title} · starts on page ${chapterContext.page}`
    : documentTitle ?? "Reader";

  return (
    <div className="z-10 border-b border-outline-variant/20 bg-[#F7F5EF]">
      <div className="flex items-center justify-between gap-3 px-4 py-2.5 md:px-6">
        <div className="min-w-0">
          <p className="text-sm font-medium text-on-surface">{pageCounterLabel}</p>
          <p className="truncate text-xs text-on-surface-variant">{summaryText}</p>
        </div>
        <button
          type="button"
          aria-label={isOpen ? "Collapse reader controls" : "Expand reader controls"}
          aria-expanded={isOpen}
          aria-controls="reader-toolbar-controls"
          onClick={onToggleOpen}
          className="inline-flex h-9 items-center gap-2 rounded-md border border-outline-variant/30 bg-white px-3 text-sm text-on-surface transition-colors hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
        >
          <span className="material-symbols-outlined text-[18px]">
            {isOpen ? "keyboard_arrow_up" : "keyboard_arrow_down"}
          </span>
          <span className="hidden sm:inline">
            {isOpen ? "Collapse reader controls" : "Expand reader controls"}
          </span>
          <span className="sm:hidden">
            {isOpen ? "Collapse" : "Expand"}
          </span>
        </button>
      </div>

      <div
        id="reader-toolbar-controls"
        aria-hidden={!isOpen}
        className={`grid transition-[grid-template-rows,opacity] duration-200 ease-out ${
          isOpen ? "grid-rows-[1fr] opacity-100" : "pointer-events-none grid-rows-[0fr] opacity-0"
        }`}
      >
        <div className="min-h-0 overflow-hidden">
          <div className="border-t border-outline-variant/20 px-4 pb-3 pt-2 md:px-6">
            <p className="text-[11px] text-on-surface-variant">
              {sequentialTurningEnabled
                ? "Tip: click page edges, use ←/→, or swipe left/right to turn."
                : "Tip: use natural scrolling in Scroll mode."}
            </p>

            <div className="mt-2 flex flex-wrap items-center gap-2 md:hidden">
              <div className="flex items-center gap-1 rounded-lg border border-outline-variant/30 bg-white p-1">
                <ToolbarButton ariaLabel="Previous page" onClick={onPrevious} disabled={isAtFirstPosition || navigationLocked}>
                  <span className="material-symbols-outlined text-[18px]">chevron_left</span>
                </ToolbarButton>
                <div className="min-w-16 px-2 text-center text-sm tabular-nums text-on-surface-variant">{zoomLabel}</div>
                <ToolbarButton ariaLabel="Next page" onClick={onNext} disabled={isAtLastPosition || navigationLocked}>
                  <span className="material-symbols-outlined text-[18px]">chevron_right</span>
                </ToolbarButton>
              </div>
              <div className="flex items-center gap-1 rounded-lg border border-outline-variant/30 bg-white p-1">
                <ToolbarButton ariaLabel="Zoom out" onClick={onZoomOut}>
                  <span className="material-symbols-outlined text-[18px]">remove</span>
                </ToolbarButton>
                <ToolbarButton ariaLabel="Zoom in" onClick={onZoomIn}>
                  <span className="material-symbols-outlined text-[18px]">add</span>
                </ToolbarButton>
              </div>
              <details className="relative">
                <summary className="inline-flex h-9 cursor-pointer list-none items-center rounded-md border border-outline-variant/30 bg-white px-3 text-sm text-on-surface transition-colors hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50">
                  More controls
                </summary>
                <div className="absolute right-0 z-20 mt-2 flex min-w-[220px] flex-col gap-1 rounded-md border border-outline-variant/30 bg-white p-2 shadow-sm">
                  <button type="button" onClick={() => onViewModeChange("single")} className="rounded px-2 py-1 text-left text-sm hover:bg-surface">Single</button>
                  <button type="button" onClick={() => onViewModeChange("double")} className="rounded px-2 py-1 text-left text-sm hover:bg-surface">Spread</button>
                  <button type="button" onClick={() => onViewModeChange("scroll")} className="rounded px-2 py-1 text-left text-sm hover:bg-surface">Scroll</button>
                  <button type="button" onClick={onFitPage} className="rounded px-2 py-1 text-left text-sm hover:bg-surface">Fit page</button>
                  <button type="button" onClick={onFitWidth} className="rounded px-2 py-1 text-left text-sm hover:bg-surface">Fit width</button>
                  <button type="button" onClick={() => onReadingModeChange("normal")} className="rounded px-2 py-1 text-left text-sm hover:bg-surface">Normal mode</button>
                  <button type="button" onClick={() => onReadingModeChange("focus")} className="rounded px-2 py-1 text-left text-sm hover:bg-surface">Focus mode</button>
                  <button type="button" onClick={() => onReadingModeChange("study")} className="rounded px-2 py-1 text-left text-sm hover:bg-surface">Study mode</button>
                </div>
              </details>
            </div>

            <div className="mt-2 hidden flex-wrap items-center gap-2 md:flex">
              <div className="flex items-center gap-1 rounded-lg border border-outline-variant/30 bg-white p-1">
                <ToolbarButton ariaLabel="Previous page" onClick={onPrevious} disabled={isAtFirstPosition || navigationLocked}>
                  <span className="material-symbols-outlined text-[18px]">chevron_left</span>
                </ToolbarButton>
                <ToolbarButton
                  ariaLabel="Single-page mode"
                  onClick={() => onViewModeChange("single")}
                  active={viewMode === "single"}
                >
                  Single
                </ToolbarButton>
                <ToolbarButton
                  ariaLabel="Two-page spread mode"
                  onClick={() => onViewModeChange("double")}
                  active={viewMode === "double"}
                >
                  Spread
                </ToolbarButton>
                <ToolbarButton
                  ariaLabel="Continuous scroll mode"
                  onClick={() => onViewModeChange("scroll")}
                  active={viewMode === "scroll"}
                >
                  Scroll
                </ToolbarButton>
                <ToolbarButton
                  ariaLabel="Next page"
                  onClick={onNext}
                  disabled={isAtLastPosition || navigationLocked}
                >
                  <span className="material-symbols-outlined text-[18px]">chevron_right</span>
                </ToolbarButton>
              </div>

              <div className="flex items-center gap-1 rounded-lg border border-outline-variant/30 bg-white p-1">
                <ToolbarButton ariaLabel="Zoom out" onClick={onZoomOut}>
                  <span className="material-symbols-outlined text-[18px]">remove</span>
                </ToolbarButton>
                <div className="min-w-16 px-2 text-center text-sm tabular-nums text-on-surface-variant">
                  {zoomLabel}
                </div>
                <ToolbarButton ariaLabel="Zoom in" onClick={onZoomIn}>
                  <span className="material-symbols-outlined text-[18px]">add</span>
                </ToolbarButton>
                <ToolbarButton
                  ariaLabel="Fit page"
                  onClick={onFitPage}
                  active={zoomMode === "fit-page"}
                >
                  Fit page
                </ToolbarButton>
                <ToolbarButton
                  ariaLabel="Fit width"
                  onClick={onFitWidth}
                  active={zoomMode === "fit-width"}
                >
                  Fit width
                </ToolbarButton>
              </div>

              <div className="flex items-center gap-1 rounded-lg border border-outline-variant/30 bg-white p-1">
                <ToolbarButton
                  ariaLabel="Normal reading mode"
                  onClick={() => onReadingModeChange("normal")}
                  active={readingMode === "normal"}
                >
                  Normal
                </ToolbarButton>
                <ToolbarButton
                  ariaLabel="Focus reading mode"
                  onClick={() => onReadingModeChange("focus")}
                >
                  Focus
                </ToolbarButton>
                <ToolbarButton
                  ariaLabel="Study reading mode"
                  onClick={() => onReadingModeChange("study")}
                  active={readingMode === "study"}
                >
                  Study
                </ToolbarButton>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
