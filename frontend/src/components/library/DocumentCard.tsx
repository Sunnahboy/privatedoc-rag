import { useState, type FocusEvent, type KeyboardEvent, type MouseEvent } from "react";
import dynamic from "next/dynamic";

import type { DocumentListItem } from "@/lib/api-client";
import { normalizeDocumentStatus } from "@/lib/api-client";
import { API_BASE_URL } from "@/lib/constants";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";

const DocumentThumbnail = dynamic(
  () => import("@/components/library/DocumentThumbnail").then((mod) => mod.DocumentThumbnail),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full items-center justify-center rounded border border-outline-variant/40 bg-surface-container-low text-xs text-on-surface-variant">
        Loading preview…
      </div>
    ),
  },
);

interface DocumentCardProps {
  document: DocumentListItem;
  onOpen: (id: string) => void;
  onDelete: (id: string) => void;
}

function getStatusLabel(status: string): string {
  const normalizedStatus = normalizeDocumentStatus(status);

  if (normalizedStatus === "indexed") {
    return "Indexed";
  }
  if (normalizedStatus === "failed") {
    return "Failed";
  }
  return "Processing";
}

function getStatusClass(status: string): string {
  const normalizedStatus = normalizeDocumentStatus(status);

  if (normalizedStatus === "indexed") {
    return "text-success";
  }
  if (normalizedStatus === "failed") {
    return "text-error";
  }
  return "text-warning";
}

export function DocumentCard({ document, onOpen, onDelete }: DocumentCardProps) {
  const normalizedStatus = normalizeDocumentStatus(document.status);
  const canOpen = normalizedStatus === "indexed";
  const fileUrl = `${API_BASE_URL}/reader/${document.document_id}/file`;
  const [isCardFocused, setIsCardFocused] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const handleOpen = () => {
    if (canOpen) {
      onOpen(document.document_id);
    }
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (!canOpen) {
      return;
    }

    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onOpen(document.document_id);
    }
  };

  const handleDeleteClick = (event: MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation();
    setIsMenuOpen(false);
    setIsDeleteDialogOpen(true);
  };

  const confirmDelete = () => {
    setIsDeleteDialogOpen(false);
    onDelete(document.document_id);
  };

  const handleFocus = () => {
    setIsCardFocused(true);
  };

  const handleBlur = (event: FocusEvent<HTMLElement>) => {
    if (event.currentTarget.contains(event.relatedTarget)) {
      return;
    }
    setIsCardFocused(false);
  };

  return (
    <article
      role={canOpen ? "button" : undefined}
      tabIndex={canOpen ? 0 : -1}
      onClick={handleOpen}
      onKeyDown={handleKeyDown}
      onFocus={handleFocus}
      onBlur={handleBlur}
      aria-label={canOpen ? `Open ${document.original_filename}` : `${document.original_filename} is not ready yet`}
      className={`group relative overflow-hidden rounded-lg border border-outline-variant/20 bg-surface-elevated transition-colors ${
        canOpen ? "cursor-pointer hover:bg-surface-container focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40" : ""
      }`}
    >
      <div className="aspect-[4/5] border-b border-outline-variant/20 bg-surface-container-low p-4">
        <DocumentThumbnail
          key={document.document_id}
          documentId={document.document_id}
          originalFilename={document.original_filename}
          fileUrl={fileUrl}
          forceBackPreview={isCardFocused}
        />
      </div>

      <div className="space-y-2 p-4">
        <p className="line-clamp-2 text-sm font-medium leading-5 text-on-surface">{document.original_filename}</p>
        <p className={`text-xs ${getStatusClass(document.status)}`}>
          {getStatusLabel(document.status)}
          {normalizedStatus === "indexed" ? ` · ${document.total_pages} pages` : ""}
        </p>
      </div>

      <details
        className="absolute right-2 top-2"
        open={isMenuOpen}
        onToggle={(event) => setIsMenuOpen((event.target as HTMLDetailsElement).open)}
      >
        <summary
          aria-label={`Document actions for ${document.original_filename}`}
          className="list-none rounded-md border border-outline-variant/40 bg-surface-elevated px-1.5 py-1 text-on-surface shadow-sm transition-colors hover:bg-surface-container focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
          onClick={(event) => event.stopPropagation()}
        >
          <span className="material-symbols-outlined text-[16px]" aria-hidden="true">
            more_horiz
          </span>
        </summary>
        <div
          className="mt-2 w-36 rounded-md border border-outline-variant/40 bg-surface-elevated p-1 shadow-lg"
          onClick={(event) => event.stopPropagation()}
        >
          <button
            type="button"
            onClick={handleDeleteClick}
            className="flex w-full items-center rounded px-2 py-1.5 text-left text-xs text-error transition-colors hover:bg-error/10"
          >
            Delete
          </button>
        </div>
      </details>

      <ConfirmDialog
        open={isDeleteDialogOpen}
        title="Delete this document?"
        description={`"${document.original_filename}" will be permanently removed from your library.`}
        confirmLabel="Delete"
        destructive
        onConfirm={confirmDelete}
        onCancel={() => setIsDeleteDialogOpen(false)}
      />
    </article>
  );
}
