"use client";

export type PDFViewMode = "single" | "double" | "scroll";
export type ReaderDisplayMode = "normal" | "focus" | "study";
export type ReaderTool = "read" | "highlight" | "draw" | "note";
export type ReaderNavigationSource =
  | "toc"
  | "toolbar"
  | "keyboard"
  | "search"
  | "bookmark"
  | "annotation"
  | "viewport"
  | "external";

export interface ReaderTocItem {
  id: string;
  level: number;
  title: string;
  page: number;
}

export interface ReaderChapterContext {
  title: string;
  level: number;
  page: number;
  index: number;
}

export type ReaderNavigationTarget =
  | {
      type: "page";
      page: number;
      source?: ReaderNavigationSource;
    }
  | {
      type: "spread";
      spreadIndex: number;
      source?: ReaderNavigationSource;
    }
  | {
      type: "annotation";
      page: number;
      annotationId: string;
      source?: ReaderNavigationSource;
    };

export interface NormalizedTocResult {
  items: ReaderTocItem[];
  parseError: boolean;
}

export type ReaderLoadState = "loading" | "ready" | "error";
export type ZoomMode = "fit-width" | "fit-page" | "custom";
export type PageChangeOrigin = "external" | "toolbar" | "keyboard" | "viewport";
export type PageTurnDirection = "forward" | "backward";

export interface PageTurnState {
  direction: PageTurnDirection;
  fromPage: number;
  toPage: number;
  phase: "start" | "running" | "dragging";
  progress: number;
  durationMs: number;
  completes: boolean;
}

export interface SwipeState {
  startX: number;
  startY: number;
  startTime: number;
}

export interface EdgeDragState {
  direction: PageTurnDirection;
  pointerId: number;
  startX: number;
  fromPage: number;
  toPage: number;
  moved: boolean;
}

export interface WindowRange {
  startIndex: number;
  endIndex: number;
}
