import { useState, useEffect, useCallback } from "react";
import { apiClient, DocumentListItem } from "@/lib/api-client";
//manage fetching the document list.
interface UseDocumentsOptions {
  autoFetch?: boolean;
}

export function useDocuments(options: UseDocumentsOptions = {}) {
  const { autoFetch = true } = options;
  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [isLoading, setIsLoading] = useState(autoFetch);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const docs = await apiClient.listDocuments();
      setDocuments(docs);
    } catch (err: unknown) {
      console.error("Failed to load documents", err);
      setError(err instanceof Error ? err.message : "Unable to load documents.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const deleteDocument = async (documentId: string) => {
    try {
      // Optimistically remove from UI
      setDocuments((prev) => prev.filter((doc) => doc.document_id !== documentId));
      // Call backend
      await apiClient.deleteDocument(documentId);
    } catch (err) {
      console.error("Failed to delete document", err);
      setError(err instanceof Error ? err.message : "Unable to delete document.");
      // Re-fetch to fix state if deletion failed
      fetchDocuments();
    }
  };

  // Fetch on mount
  useEffect(() => {
    if (autoFetch) {
      // call async to avoid setting state synchronously in the effect body
      (async () => {
        await fetchDocuments();
      })();
    }
  }, [autoFetch, fetchDocuments]);

  return { documents, isLoading, error, fetchDocuments, deleteDocument };
}