import { useState, useEffect, useCallback } from "react";
import { apiClient, DocumentListItem } from "@/lib/api-client";
//manage fetching the document list.
export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchDocuments = useCallback(async () => {
    try {
      setIsLoading(true);
      const docs = await apiClient.listDocuments();
      setDocuments(docs);
    } catch (err) {
      console.error("Failed to load documents", err);
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
      // Re-fetch to fix state if deletion failed
      fetchDocuments();
    }
  };

  // Fetch on mount
  useEffect(() => {
    // call async to avoid setting state synchronously in the effect body
    (async () => {
      await fetchDocuments();
    })();
  }, [fetchDocuments]);

  return { documents, isLoading, fetchDocuments, deleteDocument };
}