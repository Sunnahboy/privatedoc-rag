"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";

import { DocumentList } from "@/components/documents/DocumentList";
import { DocumentGrid } from "@/components/library/DocumentGrid";
import { FileUploader } from "@/components/upload/FileUploader";
import { useDocuments } from "@/hooks/useDocuments";
import { API_BASE_URL } from "@/lib/constants";

type ViewMode = "grid" | "list";
type StatusFilter = "all" | "indexed" | "processing" | "failed";
type ScopeFilter = "all" | "recent" | "starred" | "collections";

const STATUS_FILTERS: Array<{ value: StatusFilter; label: string }> = [
  { value: "all", label: "All" },
  { value: "indexed", label: "Ready" },
  { value: "processing", label: "Processing" },
  { value: "failed", label: "Failed" },
];

const SCOPE_TABS: Array<{ value: ScopeFilter; label: string; available: boolean }> = [
  { value: "all", label: "All", available: true },
  { value: "recent", label: "Recent", available: false },
  { value: "starred", label: "Starred", available: false },
  { value: "collections", label: "Collections", available: false },
];

const DocumentThumbnail = dynamic(
  () => import("@/components/library/DocumentThumbnail").then((mod) => mod.DocumentThumbnail),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full items-center justify-center rounded border border-outline-variant/40 bg-[#fdfcf8] text-xs text-on-surface-variant">
        Loading preview…
      </div>
    ),
  },
);

export default function LibraryPage() {
  const router = useRouter();
  const searchInputRef = useRef<HTMLInputElement>(null);
  const { documents, isLoading, error, fetchDocuments, deleteDocument } = useDocuments();

  const [searchQuery, setSearchQuery] = useState("");
  const [scopeFilter, setScopeFilter] = useState<ScopeFilter>("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [showUploadPanel, setShowUploadPanel] = useState(false);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchInputRef.current?.focus();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const indexedDocuments = useMemo(
    () => documents.filter((doc) => doc.status === "indexed"),
    [documents],
  );

  const filteredDocuments = useMemo(() => {
    const normalizedQuery = searchQuery.trim().toLowerCase();
    return documents.filter((doc) => {
      const matchesQuery =
        normalizedQuery.length === 0 || doc.original_filename.toLowerCase().includes(normalizedQuery);
      const matchesStatus =
        statusFilter === "all" ||
        (statusFilter === "processing"
          ? doc.status !== "indexed" && doc.status !== "failed"
          : doc.status === statusFilter);

      return matchesQuery && matchesStatus;
    });
  }, [documents, searchQuery, statusFilter]);

  const continueReadingDoc = indexedDocuments[0] ?? null;
  const hasNoDocuments = !isLoading && documents.length === 0;
  const hasNoSearchResults = !isLoading && documents.length > 0 && filteredDocuments.length === 0;
  const processingCount = documents.filter(
    (doc) => doc.status !== "indexed" && doc.status !== "failed",
  ).length;

  return (
    <div className="min-h-screen bg-[#F4F1EA] text-on-surface antialiased">
      <header className="sticky top-0 z-30 border-b border-outline-variant/20 bg-[#F7F5EF]/95 backdrop-blur">
        <div className="mx-auto flex h-14 w-full max-w-310 items-center justify-between px-4 md:px-6">
          <p className="text-base font-semibold tracking-tight text-primary">PrivateDoc</p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowUploadPanel((current) => !current)}
              className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-on-primary transition-colors hover:bg-primary/90"
              aria-expanded={showUploadPanel || hasNoDocuments}
              aria-controls="library-upload-panel"
            >
              Upload
            </button>
            <button
              type="button"
              onClick={() => void fetchDocuments()}
              aria-label="Refresh documents"
              className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-outline-variant/30 bg-white text-on-surface-variant transition-colors hover:bg-surface"
            >
              <span className="material-symbols-outlined text-[18px]" aria-hidden="true">
                refresh
              </span>
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-310 px-4 py-6 md:px-6 md:py-8">
        <section>
          <h1 className="text-2xl font-semibold tracking-tight text-on-surface">Library</h1>
          <p className="mt-1 text-sm text-on-surface-variant">Your private document workspace</p>
        </section>

        <section className="mt-5">
          <label htmlFor="library-search" className="sr-only">
            Search your documents
          </label>
          <div className="relative max-w-3xl">
            <span className="material-symbols-outlined pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[18px]">
              search
            </span>
            <input
              ref={searchInputRef}
              id="library-search"
              type="text"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Search your documents..."
              className="w-full rounded-lg border border-outline-variant/30 bg-white py-2.5 pl-10 pr-16 text-sm shadow-[0_1px_2px_rgba(0,0,0,0.03)] focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
            <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 rounded border border-outline-variant/30 bg-surface px-2 py-0.5 text-[11px] text-on-surface-variant">
              Ctrl/Cmd + K
            </span>
          </div>
        </section>

        {(showUploadPanel || hasNoDocuments) && (
          <section
            id="library-upload-panel"
            className="mt-6 rounded-lg border border-outline-variant/20 bg-white p-4 md:p-5"
          >
            <h2 className="text-sm font-semibold">Upload document</h2>
            <p className="mt-1 text-xs text-on-surface-variant">Add a PDF to your private reading library.</p>
            <div className="mt-3">
              <FileUploader compact onUploadComplete={fetchDocuments} />
            </div>
          </section>
        )}

        <section className="mt-8 rounded-lg border border-outline-variant/20 bg-white p-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-on-surface-variant">
            {continueReadingDoc ? "Recently Indexed" : "Continue Reading"}
          </p>
          {continueReadingDoc ? (
            <button
              type="button"
              onClick={() => router.push(`/workspace/${continueReadingDoc.document_id}`)}
              className="mt-3 w-full rounded-lg border border-outline-variant/20 bg-[#f8f6f1] p-4 text-left transition-colors hover:bg-[#f2efe7]"
            >
              <div className="flex items-start gap-4">
                <div className="w-16 shrink-0 sm:w-20 md:w-24 lg:w-20 xl:w-24">
                  <div className="aspect-4/5  overflow-hidden rounded-md border border-outline-variant/30 bg-white">
                    <DocumentThumbnail
                      documentId={continueReadingDoc.document_id}
                      originalFilename={continueReadingDoc.original_filename}
                      fileUrl={`${API_BASE_URL}/reader/${continueReadingDoc.document_id}/file`}
                    />
                  </div>
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-base font-semibold">{continueReadingDoc.original_filename}</p>
                  <p className="mt-1 text-sm text-on-surface-variant">
                    Indexed · {continueReadingDoc.total_pages} pages
                  </p>
                  <p className="mt-3 text-sm font-medium text-primary">Continue reading →</p>
                </div>
              </div>
            </button>
          ) : (
            <div className="mt-3 rounded-lg border border-dashed border-outline-variant/40 px-5 py-6 text-sm text-on-surface-variant">
              Your library is empty. Upload a document to start building your private reading library.
            </div>
          )}
        </section>

        <section className="mt-8">
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h2 className="text-base font-semibold">Your documents</h2>
                <p className="text-xs text-on-surface-variant">
                  {documents.length} documents · {indexedDocuments.length} ready
                  {processingCount > 0 ? ` · ${processingCount} processing` : ""}
                </p>
              </div>

              <div className="flex items-center gap-2 self-start rounded-md border border-outline-variant/20 bg-white p-1">
                <button
                  type="button"
                  onClick={() => setViewMode("grid")}
                  className={`inline-flex items-center rounded px-2 py-1 text-xs transition-colors ${
                    viewMode === "grid" ? "bg-primary/10 text-primary" : "text-on-surface-variant hover:bg-surface"
                  }`}
                  aria-pressed={viewMode === "grid"}
                >
                  Grid
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode("list")}
                  className={`inline-flex items-center rounded px-2 py-1 text-xs transition-colors ${
                    viewMode === "list" ? "bg-primary/10 text-primary" : "text-on-surface-variant hover:bg-surface"
                  }`}
                  aria-pressed={viewMode === "list"}
                >
                  List
                </button>
              </div>
            </div>

            <nav aria-label="Document scopes" className="flex flex-wrap gap-2">
              {SCOPE_TABS.map((tab) => {
                const isActive = scopeFilter === tab.value;
                return (
                  <button
                    key={tab.value}
                    type="button"
                    onClick={() => tab.available && setScopeFilter(tab.value)}
                    disabled={!tab.available}
                    aria-disabled={!tab.available}
                    title={tab.available ? tab.label : `${tab.label} is not available yet`}
                    className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                      isActive
                        ? "border-primary/40 bg-primary/10 text-primary"
                        : "border-outline-variant/30 bg-white text-on-surface-variant"
                    } ${tab.available ? "hover:bg-surface" : "cursor-not-allowed opacity-60"}`}
                  >
                    {tab.label}
                  </button>
                );
              })}
            </nav>

            <div className="flex flex-wrap gap-2">
              {STATUS_FILTERS.map((filter) => {
                const isActive = statusFilter === filter.value;
                return (
                  <button
                    key={filter.value}
                    type="button"
                    onClick={() => setStatusFilter(filter.value)}
                    className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                      isActive
                        ? "border-primary/40 bg-primary/10 text-primary"
                        : "border-outline-variant/30 bg-white text-on-surface-variant hover:bg-surface"
                    }`}
                  >
                    {filter.label}
                  </button>
                );
              })}
            </div>
          </div>

          {error && (
            <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              Unable to refresh your library right now. Please try again.
            </div>
          )}

          <div className="mt-4">
            {hasNoSearchResults ? (
              <div className="rounded-lg border border-outline-variant/20 bg-white px-5 py-8 text-center text-sm text-on-surface-variant">
                No documents found. Try a different search or filter.
              </div>
            ) : viewMode === "grid" ? (
              <DocumentGrid
                documents={filteredDocuments}
                isLoading={isLoading}
                onOpenDocument={(id) => router.push(`/workspace/${id}`)}
                onDeleteDocument={deleteDocument}
              />
            ) : (
              <DocumentList
                documents={filteredDocuments}
                isLoading={isLoading}
                onDeleteDocument={deleteDocument}
                onOpenDocument={(id) => router.push(`/workspace/${id}`)}
              />
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
