import type { DocumentListItem } from "@/lib/api-client";

import { DocumentCard } from "@/components/library/DocumentCard";

interface DocumentGridProps {
  documents: DocumentListItem[];
  isLoading: boolean;
  onOpenDocument: (id: string) => void;
  onDeleteDocument: (id: string) => void;
}

export function DocumentGrid({
  documents,
  isLoading,
  onOpenDocument,
  onDeleteDocument,
}: DocumentGridProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, index) => (
          <div key={`doc-grid-skeleton-${index}`} className="overflow-hidden rounded-lg border border-outline-variant/20 bg-white">
            <div className="aspect-4/5 animate-pulse bg-surface-container-low" />
            <div className="space-y-2 p-4">
              <div className="h-4 w-4/5 animate-pulse rounded bg-surface-container" />
              <div className="h-3 w-2/5 animate-pulse rounded bg-surface-container-low" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="rounded-lg border border-outline-variant/20 bg-white px-5 py-8 text-center text-sm text-on-surface-variant">
        No documents found. Try a different search or filter.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {documents.map((document) => (
        <DocumentCard
          key={document.document_id}
          document={document}
          onOpen={onOpenDocument}
          onDelete={onDeleteDocument}
        />
      ))}
    </div>
  );
}
