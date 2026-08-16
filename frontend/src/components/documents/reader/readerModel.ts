"use client";

import type { NormalizedTocResult, ReaderChapterContext, ReaderNavigationTarget, ReaderTocItem } from "./readerTypes";

export type {
  NormalizedTocResult,
  PDFViewMode,
  ReaderChapterContext,
  ReaderNavigationTarget,
  ReaderDisplayMode,
  ReaderNavigationSource,
  ReaderTocItem,
  ReaderTool,
} from "./readerTypes";

function toPositiveNumber(value: unknown, fallback: number): number {
  if (typeof value === "number" && Number.isFinite(value) && value > 0) {
    return Math.floor(value);
  }

  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed) && parsed > 0) {
      return Math.floor(parsed);
    }
  }

  return fallback;
}

function toText(value: unknown, fallback: string): string {
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (trimmed.length > 0) {
      return trimmed;
    }
  }

  return fallback;
}

function normalizeTocEntry(item: unknown, index: number): ReaderTocItem | null {
  if (Array.isArray(item)) {
    return {
      id: `toc-${index}`,
      level: toPositiveNumber(item[0], 1),
      title: toText(item[1], "Untitled Section"),
      page: toPositiveNumber(item[2], 1),
    };
  }

  if (item && typeof item === "object") {
    const record = item as Record<string, unknown>;
    return {
      id: `toc-${index}`,
      level: toPositiveNumber(record.level, 1),
      title: toText(record.title ?? record.text, "Untitled Section"),
      page: toPositiveNumber(record.page ?? record.page_number ?? record.pageNum, 1),
    };
  }

  return null;
}

export function normalizeToc(rawToc: unknown): NormalizedTocResult {
  if (!rawToc) {
    return { items: [], parseError: false };
  }

  let resolved = rawToc;
  if (typeof resolved === "string") {
    try {
      resolved = JSON.parse(resolved);
    } catch {
      return { items: [], parseError: true };
    }
  }

  if (!Array.isArray(resolved)) {
    return { items: [], parseError: true };
  }

  const items = resolved
    .map((item, index) => normalizeTocEntry(item, index))
    .filter((item): item is ReaderTocItem => item !== null);

  return { items, parseError: false };
}

export function getChapterContext(toc: ReaderTocItem[], currentPage: number): ReaderChapterContext | null {
  let active: ReaderChapterContext | null = null;

  toc.forEach((item, index) => {
    if (item.page > currentPage) {
      return;
    }

    if (
      !active ||
      item.page > active.page ||
      (item.page === active.page && item.level >= active.level)
    ) {
      active = {
        title: item.title,
        level: item.level,
        page: item.page,
        index,
      };
    }
  });

  return active;
}

export function clampPage(page: number, totalPages?: number | null): number {
  const safeTotalPages = Math.max(1, totalPages ?? 1);
  if (!Number.isFinite(page)) {
    return 1;
  }

  return Math.min(safeTotalPages, Math.max(1, Math.floor(page)));
}

export function clampZoomScale(scale: number): number {
  if (!Number.isFinite(scale)) {
    return 1;
  }

  return Math.min(2.5, Math.max(0.5, scale));
}

export function getSpreadCount(totalPages?: number | null): number {
  const pages = Math.max(0, totalPages ?? 0);
  if (pages === 0) {
    return 0;
  }

  return 1 + Math.ceil(Math.max(0, pages - 1) / 2);
}

export function getSpreadIndexForPage(page: number): number {
  const safePage = Math.max(1, Math.floor(page));
  if (safePage === 1) {
    return 0;
  }

  return Math.floor((safePage - 2) / 2) + 1;
}

export function getSpreadPages(
  spreadIndex: number,
  totalPages?: number | null,
): { leftPage: number | null; rightPage: number | null } {
  const pages = Math.max(0, totalPages ?? 0);
  if (pages === 0) {
    return { leftPage: null, rightPage: null };
  }

  if (spreadIndex <= 0) {
    return {
      leftPage: null,
      rightPage: 1,
    };
  }

  const leftPage = spreadIndex * 2;
  const rightPage = leftPage + 1;

  return {
    leftPage: leftPage <= pages ? leftPage : null,
    rightPage: rightPage <= pages ? rightPage : null,
  };
}

export function getPrimaryPageForSpread(spreadIndex: number, totalPages?: number | null): number {
  const spread = getSpreadPages(spreadIndex, totalPages);
  return spread.leftPage ?? spread.rightPage ?? 1;
}

export function spreadContainsPage(
  spreadIndex: number,
  page: number,
  totalPages?: number | null,
): boolean {
  const spread = getSpreadPages(spreadIndex, totalPages);
  return spread.leftPage === page || spread.rightPage === page;
}

export function resolveNavigationTarget(
  target: ReaderNavigationTarget,
  totalPages?: number | null,
): number {
  if (target.type === "spread") {
    return clampPage(getPrimaryPageForSpread(target.spreadIndex, totalPages), totalPages);
  }

  return clampPage(target.page, totalPages);
}
