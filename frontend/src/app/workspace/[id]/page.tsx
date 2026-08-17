"use client";

import {
  use,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type MouseEvent,
  type KeyboardEvent as ReactKeyboardEvent,
  type PointerEvent as ReactPointerEvent,
  type CSSProperties,
} from "react";
import dynamic from "next/dynamic";
import Link from "next/link";

import {
  getChapterContext,
  normalizeToc,
  resolveNavigationTarget,
  type PDFViewMode,
  type ReaderDisplayMode,
  type ReaderNavigationTarget,
  type ReaderTocItem,
} from "@/components/documents/reader/readerModel";
import { API_BASE_URL } from "@/lib/constants";

const PDFViewer = dynamic(() => import("@/components/documents/PDFViewer"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full min-h-[60vh] items-center justify-center bg-[#F4F1EA] text-on-surface-variant">
      Preparing reader…
    </div>
  ),
});
const RagChat = dynamic(() => import("@/components/chat/RagChat").then((mod) => mod.RagChat), {
  ssr: false,
  loading: () => <div className="p-4 text-sm text-on-surface-variant">Preparing RAG Chat…</div>,
});

interface ReaderDocumentResponse {
  original_filename: string;
  total_pages: number;
  toc: unknown;
}

type DocumentLoadState = "loading" | "ready" | "error";
type ResizeTarget = "header" | "toc" | "chat" | null;

const LAYOUT_STORAGE_KEY = "privatedoc.reader-layout";
const TOOLBAR_OPEN_STORAGE_KEY = "privatedoc.reader-toolbar-open";
const DEFAULT_LAYOUT = { tocWidth: 320, chatWidth: 352, headerHeight: 72 };
const TOC_WIDTH = { min: 220, max: 420 };
const CHAT_WIDTH = { min: 300, max: 560 };
const HEADER_HEIGHT = { min: 52, max: 128 };

function clamp(value: number, minimum: number, maximum: number) {
  return Math.min(maximum, Math.max(minimum, value));
}

function getInitialLayout() {
  if (typeof window === "undefined") return DEFAULT_LAYOUT;
  try {
    const saved = window.localStorage.getItem(LAYOUT_STORAGE_KEY);
    if (!saved) return DEFAULT_LAYOUT;
    const candidate = JSON.parse(saved) as Partial<typeof DEFAULT_LAYOUT>;
    return {
      tocWidth: clamp(candidate.tocWidth ?? DEFAULT_LAYOUT.tocWidth, TOC_WIDTH.min, TOC_WIDTH.max),
      chatWidth: clamp(candidate.chatWidth ?? DEFAULT_LAYOUT.chatWidth, CHAT_WIDTH.min, CHAT_WIDTH.max),
      headerHeight: clamp(candidate.headerHeight ?? DEFAULT_LAYOUT.headerHeight, HEADER_HEIGHT.min, HEADER_HEIGHT.max),
    };
  } catch {
    return DEFAULT_LAYOUT;
  }
}

function buildReaderRequest(id: string): string {
  return `${API_BASE_URL}/reader/${id}`;
}

function getInitialTocOpen(): boolean {
  if (typeof window === "undefined") {
    return true;
  }

  return window.innerWidth >= 768;
}

function getInitialStudyOpen(): boolean {
  if (typeof window === "undefined") {
    return true;
  }

  return window.innerWidth >= 1280;
}

function getInitialToolbarOpen(): boolean {
  if (typeof window === "undefined") {
    return true;
  }

  const persisted = window.localStorage.getItem(TOOLBAR_OPEN_STORAGE_KEY);
  if (persisted === "true") {
    return true;
  }
  if (persisted === "false") {
    return false;
  }

  return window.innerWidth >= 1024;
}

function PanelButton({
  label,
  icon,
  onClick,
  active,
}: {
  label: string;
  icon: string;
  onClick: () => void;
  active?: boolean;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      className={`inline-flex h-10 items-center gap-2 rounded-md border px-3 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 ${
        active
          ? "border-primary/30 bg-primary/10 text-primary"
          : "border-outline-variant/30 bg-white text-on-surface hover:bg-surface"
      }`}
    >
      <span className="material-symbols-outlined text-[18px]">{icon}</span>
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
}

export default function WorkspacePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);

  const [doc, setDoc] = useState<ReaderDocumentResponse | null>(null);
  const [loadState, setLoadState] = useState<DocumentLoadState>("loading");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [viewMode, setViewMode] = useState<PDFViewMode>("double");
  const [readingMode, setReadingMode] = useState<ReaderDisplayMode>("normal");
  const [isTocOpen, setIsTocOpen] = useState(getInitialTocOpen);
  const [isAiOpen, setIsAiOpen] = useState(getInitialStudyOpen);
  const [isReaderToolbarOpen, setIsReaderToolbarOpen] = useState(getInitialToolbarOpen);
  const [isRagExpanded, setIsRagExpanded] = useState(false);
  const [collapsedSections, setCollapsedSections] = useState<Set<number>>(new Set());
  const [layout, setLayout] = useState(getInitialLayout);
  const [resizeTarget, setResizeTarget] = useState<ResizeTarget>(null);
  const resizeStartRef = useRef<{ target: Exclude<ResizeTarget, null>; position: number; value: number } | null>(null);

  useEffect(() => {
    try {
      window.localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify(layout));
    } catch {
      // Storage can be unavailable in private browsing contexts.
    }
  }, [layout]);

  useEffect(() => {
    try {
      window.localStorage.setItem(TOOLBAR_OPEN_STORAGE_KEY, String(isReaderToolbarOpen));
    } catch {
      // Storage can be unavailable in private browsing contexts.
    }
  }, [isReaderToolbarOpen]);

  const startResize = useCallback((target: Exclude<ResizeTarget, null>, event: ReactPointerEvent<HTMLButtonElement>) => {
    if (window.innerWidth < 768) return;
    const value = target === "header" ? layout.headerHeight : target === "toc" ? layout.tocWidth : layout.chatWidth;
    resizeStartRef.current = { target, position: target === "header" ? event.clientY : event.clientX, value };
    setResizeTarget(target);
    event.currentTarget.setPointerCapture(event.pointerId);
    event.preventDefault();
  }, [layout]);

  const moveResize = useCallback((event: ReactPointerEvent<HTMLButtonElement>) => {
    const start = resizeStartRef.current;
    if (!start) return;
    const delta = (start.target === "header" ? event.clientY : event.clientX) - start.position;
    setLayout((current) => {
      if (start.target === "header") return { ...current, headerHeight: clamp(start.value + delta, HEADER_HEIGHT.min, HEADER_HEIGHT.max) };
      if (start.target === "toc") return { ...current, tocWidth: clamp(start.value + delta, TOC_WIDTH.min, TOC_WIDTH.max) };
      return { ...current, chatWidth: clamp(start.value - delta, CHAT_WIDTH.min, CHAT_WIDTH.max) };
    });
  }, []);

  const endResize = useCallback((event: ReactPointerEvent<HTMLButtonElement>) => {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
    resizeStartRef.current = null;
    setResizeTarget(null);
  }, []);

  const resizeWithKeyboard = useCallback((target: Exclude<ResizeTarget, null>, event: ReactKeyboardEvent<HTMLButtonElement>) => {
    const decrease = target === "header" ? event.key === "ArrowUp" : event.key === "ArrowLeft";
    const increase = target === "header" ? event.key === "ArrowDown" : event.key === "ArrowRight";
    if (!decrease && !increase && event.key !== "Home" && event.key !== "End") return;
    event.preventDefault();
    setLayout((current) => {
      const bounds = target === "header" ? HEADER_HEIGHT : target === "toc" ? TOC_WIDTH : CHAT_WIDTH;
      const key = target === "header" ? "headerHeight" : target === "toc" ? "tocWidth" : "chatWidth";
      const next = event.key === "Home" ? bounds.min : event.key === "End" ? bounds.max : clamp(current[key] + (increase ? 16 : -16), bounds.min, bounds.max);
      return { ...current, [key]: next };
    });
  }, []);

  const hydrateDocument = useCallback(async (signal?: AbortSignal) => {
    try {
      const response = await fetch(buildReaderRequest(id), { signal });
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error("This document could not be found.");
        }

        throw new Error("The document is currently unavailable.");
      }

      const data = (await response.json()) as ReaderDocumentResponse;
      setDoc(data);
      setCurrentPage(1);
      setCollapsedSections(new Set());
      setLoadState("ready");
    } catch (error) {
      if (signal?.aborted) {
        return;
      }

      const message = error instanceof Error
        ? error.message
        : "We couldn’t reach the document service.";
      setDoc(null);
      setLoadError(message);
      setLoadState("error");
    }
  }, [id]);

  useEffect(() => {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => {
      void hydrateDocument(controller.signal);
    }, 0);

    return () => {
      window.clearTimeout(timeoutId);
      controller.abort();
    };
  }, [hydrateDocument]);

  const loadDocument = useCallback(async () => {
    setLoadState("loading");
    setLoadError(null);
    await hydrateDocument();
  }, [hydrateDocument]);

  const applyReadingMode = useCallback((nextMode: ReaderDisplayMode) => {
    setReadingMode(nextMode);
    if (nextMode === "study") {
      setIsAiOpen(true);
    }
  }, []);

  const tocResult = useMemo(() => normalizeToc(doc?.toc), [doc?.toc]);
  const tocItems = tocResult.items;
  const chapterContext = useMemo(
    () => getChapterContext(tocItems, currentPage),
    [currentPage, tocItems],
  );

  const navigateReader = useCallback(
    (target: ReaderNavigationTarget) => {
      setCurrentPage(resolveNavigationTarget(target, doc?.total_pages));
    },
    [doc?.total_pages],
  );

  const toggleCollapse = useCallback((index: number, event: MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation();
    setCollapsedSections((current) => {
      const next = new Set(current);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  }, []);

  const hasChildren = useCallback(
    (index: number) => {
      if (index + 1 >= tocItems.length) {
        return false;
      }

      return tocItems[index + 1].level > tocItems[index].level;
    },
    [tocItems],
  );

  const isHiddenByCollapsedParent = useCallback(
    (index: number) => {
      let currentLevel = tocItems[index].level;

      for (let cursor = index - 1; cursor >= 0; cursor -= 1) {
        const previousLevel = tocItems[cursor].level;
        if (previousLevel < currentLevel) {
          if (collapsedSections.has(cursor)) {
            return true;
          }
          currentLevel = previousLevel;
        }
      }

      return false;
    },
    [collapsedSections, tocItems],
  );

  const fileUrl = `${API_BASE_URL}/reader/${id}/file`;

  if (loadState === "loading") {
    return (
      <div className="flex h-screen items-center justify-center bg-[#F4F1EA] px-6 text-center text-on-surface">
        <div>
          <p className="text-lg font-medium">Opening workspace…</p>
          <p className="mt-2 text-sm text-on-surface-variant">
            Fetching the document record and preparing the reading environment.
          </p>
        </div>
      </div>
    );
  }

  if (loadState === "error" || !doc) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#F4F1EA] px-6">
        <div className="max-w-md rounded-2xl border border-outline-variant/30 bg-white p-6 text-center shadow-sm">
          <p className="text-lg font-medium text-on-surface">Unable to open this document.</p>
          <p className="mt-2 text-sm text-on-surface-variant">
            {loadError ?? "The document may be unavailable or the server may not be responding."}
          </p>
          <button
            type="button"
            onClick={() => void loadDocument()}
            className="mt-4 inline-flex items-center rounded-md border border-outline-variant/30 px-4 py-2 text-sm font-medium text-on-surface transition-colors hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  const isFocusMode = readingMode === "focus";
  // Modes affect visibility, never the user's saved panel dimensions or preferences.
  const effectiveTocOpen = !isFocusMode && isTocOpen;
  const effectiveAiOpen = !isFocusMode && isAiOpen;
  const tocPanelClass = isFocusMode || !effectiveTocOpen ? "-translate-x-full" : "translate-x-0";
  const aiPanelClass = isFocusMode || !effectiveAiOpen ? "translate-x-full" : "translate-x-0 w-full sm:w-96";

  return (
    <div className="flex h-screen w-full flex-col overflow-hidden bg-[#F4F1EA] text-on-surface antialiased">
      {!isFocusMode && (
        <header
          style={{ height: layout.headerHeight }}
          className={`relative z-40 shrink-0 overflow-hidden border-b border-outline-variant/20 bg-[#F7F5EF] transition-[height] duration-200 ${resizeTarget === "header" ? "transition-none! select-none" : ""}`}
        >
          <div className="flex h-full items-center justify-between gap-3 px-4 md:px-6">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold md:text-base">
              <Link href="/library" className="mr-2 text-on-surface-variant hover:text-primary">
                Library
              </Link>
              / {doc.original_filename}
            </p>
            <p className={`truncate text-xs text-on-surface-variant ${layout.headerHeight < 68 ? "hidden" : ""}`}>
              {chapterContext
                ? `${chapterContext.title} · Page ${currentPage}`
                : `Page ${currentPage}${doc.total_pages ? ` of ${doc.total_pages}` : ""}`}
            </p>
          </div>

          <div className="hidden items-center gap-2 lg:flex">
            <PanelButton
              label="Normal"
              icon="import_contacts"
              active={readingMode === "normal"}
              onClick={() => applyReadingMode("normal")}
            />
            <PanelButton
              label="Focus"
              icon="center_focus_strong"
              active={false}
              onClick={() => applyReadingMode("focus")}
            />
            <PanelButton
              label="Study"
              icon="auto_stories"
              active={readingMode === "study"}
              onClick={() => applyReadingMode("study")}
            />
          </div>

          <div className="flex items-center gap-2">
            <PanelButton
              label={isTocOpen ? "Hide contents" : "Show contents"}
              icon="menu_book"
              active={effectiveTocOpen}
              onClick={() => setIsTocOpen((current) => !current)}
            />
            <PanelButton
              label={isAiOpen ? "Hide RAG Chat" : "Show RAG Chat"}
              icon="storage"
              active={effectiveAiOpen}
              onClick={() => setIsAiOpen((current) => !current)}
            />
          </div>
          </div>
          <button
            type="button"
            aria-label="Resize reader controls"
            title="Drag to resize reader controls; double-click to reset"
            onPointerDown={(event) => startResize("header", event)}
            onPointerMove={moveResize}
            onPointerUp={endResize}
            onPointerCancel={endResize}
            onKeyDown={(event) => resizeWithKeyboard("header", event)}
            onDoubleClick={() => setLayout((current) => ({ ...current, headerHeight: DEFAULT_LAYOUT.headerHeight }))}
            className="reader-resize-handle reader-resize-handle-row absolute inset-x-0 bottom-0 z-50 h-3 cursor-row-resize touch-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/60"
          ><span aria-hidden="true" /></button>
        </header>
      )}

      <div className="relative flex min-h-0 flex-1 overflow-hidden">
        {!isFocusMode && effectiveAiOpen && (
          <button
            type="button"
            aria-label="Close RAG Chat drawer"
            className="fixed inset-0 z-20 bg-black/20 xl:hidden"
            onClick={() => setIsAiOpen(false)}
          />
        )}

        {!isFocusMode && effectiveTocOpen && (
          <button
            type="button"
            aria-label="Close contents drawer"
            className="fixed inset-0 z-20 bg-black/20 md:hidden"
            onClick={() => setIsTocOpen(false)}
          />
        )}

        {!isFocusMode && (
          <aside
            style={{ "--toc-width": `${layout.tocWidth}px`, "--reader-header-height": `${layout.headerHeight}px` } as CSSProperties}
            className={`fixed bottom-0 left-0 top-var(--reader-header-height) z-30 w-80 min-w-0 overflow-y-auto border-r border-outline-variant/20
               bg-[#F7F5EF] transition-all duration-300 md:relative md:top-auto md:z-0 ${effectiveTocOpen ? "md:w-(--toc-width) md:border-r" : "md:w-0 md:border-r-0"} 
               ${resizeTarget === "toc" ? "md:transition-none! md:select-none" : ""} ${tocPanelClass}`}
          >
          <div className="p-4">
            <div className="mb-4">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-on-surface-variant">
                Contents
              </p>
              <p className="mt-1 text-xs text-on-surface-variant">
                Navigate by chapter, section, or starting page.
              </p>
            </div>

            <nav className="flex flex-col gap-0.5 pb-10" aria-label="Table of contents">
              {tocResult.parseError ? (
                <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                  Error loading TOC structure.
                </div>
              ) : tocItems.length === 0 ? (
                <div className="p-2 text-sm italic text-on-surface-variant/70">
                  No Table of Contents embedded in this document.
                </div>
              ) : (
                tocItems.map((item: ReaderTocItem, index: number) => {
                  if (isHiddenByCollapsedParent(index)) {
                    return null;
                  }

                  const hasSubItems = hasChildren(index);
                  const isCollapsed = collapsedSections.has(index);

                  return (
                    <div
                      key={item.id}
                      onClick={() => navigateReader({ type: "page", page: item.page, source: "toc" })}
                      className={`group flex cursor-pointer items-center justify-between rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-surface hover:text-primary ${
                        currentPage === item.page ? "bg-primary/8 text-primary" : ""
                      }`}
                      style={{ paddingLeft: `${(item.level - 1) * 12 + 8}px` }}
                    >
                      <div className="mr-2 flex min-w-0 items-center gap-1.5">
                        {hasSubItems ? (
                          <button
                            type="button"
                            aria-label={isCollapsed ? `Expand ${item.title}` : `Collapse ${item.title}`}
                            onClick={(event) => toggleCollapse(index, event)}
                            className="shrink-0 rounded p-0.5 text-on-surface-variant transition-colors hover:bg-surface-dim focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
                          >
                            <span className="material-symbols-outlined text-[16px]">
                              {isCollapsed ? "chevron_right" : "expand_more"}
                            </span>
                          </button>
                        ) : (
                          <span className="w-4 shrink-0" aria-hidden="true" />
                        )}

                        <span className="truncate text-on-surface/85 group-hover:text-primary">
                          {item.title}
                        </span>
                      </div>

                      <span className="shrink-0 text-xs text-on-surface-variant/60 group-hover:text-primary/70">
                        {item.page}
                      </span>
                    </div>
                  );
                })
              )}
            </nav>
          </div>
          {effectiveTocOpen && (
            <button type="button" aria-label="Resize table of contents" title="Resize table of contents" onPointerDown={(event) => startResize("toc", event)} onPointerMove={moveResize} onPointerUp={endResize} onPointerCancel={endResize} onKeyDown={(event) => resizeWithKeyboard("toc", event)} className="reader-resize-handle reader-resize-handle-col absolute inset-y-0 right-0 z-40 hidden w-3 cursor-col-resize touch-none md:block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/60"><span aria-hidden="true" /></button>
          )}
          </aside>
        )}

        <main className="min-w-0 flex-1 overflow-hidden">
          <PDFViewer
            fileUrl={fileUrl}
            pageNumber={currentPage}
            totalPages={doc.total_pages}
            viewMode={viewMode}
            readingMode={readingMode}
            isToolbarOpen={isReaderToolbarOpen}
            documentTitle={doc.original_filename}
            chapterContext={chapterContext}
            onPageChange={setCurrentPage}
            onViewModeChange={setViewMode}
            onReadingModeChange={applyReadingMode}
            onToggleToolbar={() => setIsReaderToolbarOpen((current) => !current)}
          />
        </main>

        {!isFocusMode && (
          <aside
            style={{ "--chat-width": `${isRagExpanded ? CHAT_WIDTH.max : layout.chatWidth}px`, "--reader-header-height": `${layout.headerHeight}px` } as CSSProperties}
            className={`fixed bottom-0 right-0 top-var(--reader-header-height) z-30 w-96 min-w-0 overflow-hidden border-l border-outline-variant/20 bg-white transition-all duration-300 xl:relative xl:top-auto xl:z-0 ${effectiveAiOpen ? "xl:w-(--chat-width) xl:border-l" : "xl:w-0 xl:border-l-0"} ${resizeTarget === "chat" ? "xl:transition-none! xl:select-none" : ""} ${aiPanelClass}`}
          >
            {effectiveAiOpen && (
              <button type="button" aria-label="Resize RAG Chat" title="Resize RAG Chat" onPointerDown={(event) => startResize("chat", event)} onPointerMove={moveResize} onPointerUp={endResize} onPointerCancel={endResize} onKeyDown={(event) => resizeWithKeyboard("chat", event)} className="reader-resize-handle reader-resize-handle-col absolute inset-y-0 left-0 z-40 hidden w-3 cursor-col-resize touch-none xl:block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/60"><span aria-hidden="true" /></button>
            )}
            <RagChat
              documentId={id}
              currentPage={currentPage}
              showDocumentSelector={false}
              isExpanded={isRagExpanded}
              onToggleExpanded={() => setIsRagExpanded((current) => !current)}
              className="h-full rounded-none border-0"
            />
          </aside>
        )}
      </div>

      {!isFocusMode && (
        <div className="fixed inset-x-4 bottom-4 z-40 md:hidden">
          <div className="mx-auto flex max-w-sm items-center justify-between rounded-full border border-outline-variant/20 bg-white px-3 py-2 shadow-lg">
            <button
              type="button"
              onClick={() => setIsTocOpen(true)}
              className="inline-flex items-center gap-2 rounded-full px-3 py-2 text-sm text-on-surface transition-colors hover:bg-surface"
            >
              <span className="material-symbols-outlined text-[18px]">menu_book</span>
              Contents
            </button>
            <button
              type="button"
              onClick={() => applyReadingMode("focus")}
              className="inline-flex items-center gap-2 rounded-full px-3 py-2 text-sm text-on-surface transition-colors hover:bg-surface"
            >
              <span className="material-symbols-outlined text-[18px]">center_focus_strong</span>
              Focus
            </button>
            <button
              type="button"
              onClick={() => setIsAiOpen(true)}
              className="inline-flex items-center gap-2 rounded-full px-3 py-2 text-sm text-on-surface transition-colors hover:bg-surface"
            >
              <span className="material-symbols-outlined text-[18px]">auto_awesome</span>
              RAG Chat
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
