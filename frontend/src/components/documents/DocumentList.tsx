import { DocumentListItem, normalizeDocumentStatus } from "@/lib/api-client";

interface DocumentListProps {
  documents: DocumentListItem[];
  isLoading: boolean;
  selectedIds?: string[];
  onToggleSelection?: (id: string) => void;
  onDeleteDocument: (id: string) => void;
  onOpenDocument?: (id: string) => void;
  showSelection?: boolean;
}

function getStatusChipClass(status: string): string {
  const normalizedStatus = normalizeDocumentStatus(status);

  if (normalizedStatus === "indexed") {
    return "bg-green-100 text-green-700";
  }
  if (normalizedStatus === "failed") {
    return "bg-red-100 text-red-700";
  }
  return "bg-amber-100 text-amber-700";
}

export function DocumentList({
  documents,
  isLoading,
  selectedIds = [],
  onToggleSelection,
  onDeleteDocument,
  onOpenDocument,
  showSelection = false,
}: DocumentListProps) {
  if (isLoading) {
    return (
      <div className="divide-y divide-outline-variant/20 rounded-lg border border-outline-variant/20 bg-white">
        {Array.from({ length: 5 }).map((_, index) => (
          <div key={`doc-skeleton-${index}`} className="animate-pulse px-4 py-3">
            <div className="h-4 w-2/5 rounded bg-surface-container" />
            <div className="mt-2 h-3 w-1/4 rounded bg-surface-container-low" />
          </div>
        ))}
      </div>
    );
  }

  if (documents.length === 0) {
    return <div className="py-8 text-center text-sm text-on-surface-variant">No documents available.</div>;
  }

  return (
    <div className="overflow-hidden rounded-lg border border-outline-variant/20 bg-white">
      {documents.map((doc) => {
        const selected = selectedIds.includes(doc.document_id);
        const normalizedStatus = normalizeDocumentStatus(doc.status);
        const canOpen = normalizedStatus === "indexed";

        return (
          <div
            key={doc.document_id}
            className={`flex items-start gap-3 border-b border-outline-variant/20 px-4 py-3 transition-colors last:border-b-0 ${
              selected ? "bg-primary/5" : "bg-white hover:bg-surface-container-low/50"
            }`}
          >
            {showSelection && onToggleSelection && (
              <input
                type="checkbox"
                aria-label={`Select ${doc.original_filename}`}
                className="mt-1 h-4 w-4 cursor-pointer rounded border-outline-variant text-primary focus:ring-primary/40"
                checked={selected}
                onChange={() => onToggleSelection(doc.document_id)}
              />
            )}

              <div className="min-w-0 flex-1">
                <p
                  className={`truncate text-sm font-medium ${
                    canOpen ? "text-on-surface hover:text-primary" : "text-on-surface"
                  }`}
                  title={doc.original_filename}
                >
                  {doc.original_filename}
                </p>
                <div className="mt-1 flex items-center gap-2">
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${getStatusChipClass(doc.status)}`}>
                    {normalizedStatus}
                  </span>
                  {normalizedStatus === "indexed" && (
                    <span className="text-xs text-on-surface-variant">
                      {doc.total_pages} pages
                    </span>
                  )}
                </div>
              </div>

            <div className="flex items-center gap-2">
              {canOpen && onOpenDocument && (
                <button
                  type="button"
                  onClick={() => onOpenDocument(doc.document_id)}
                  className="rounded-md border border-outline-variant/30 px-2 py-1 text-xs text-on-surface transition-colors hover:bg-surface"
                >
                  Open
                </button>
              )}

              <button
                type="button"
                onClick={() => {
                  if (window.confirm("Are you sure you want to delete this document?")) {
                    onDeleteDocument(doc.document_id);
                  }
                }}
                className="rounded p-1.5 text-on-surface-variant transition-colors hover:bg-red-50 hover:text-red-600"
                title="Delete document"
                aria-label={`Delete ${doc.original_filename}`}
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}