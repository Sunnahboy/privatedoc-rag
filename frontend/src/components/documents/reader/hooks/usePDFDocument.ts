"use client";

import { useCallback, useMemo, useState } from "react";

import type { ReaderLoadState } from "../readerTypes";

function formatDocumentError(message?: string | null): string {
  if (!message) {
    return "The file may be unavailable, corrupt, or blocked by the browser.";
  }

  if (message.includes("Invalid PDF") || message.includes("InvalidPDF") || message.includes("structure")) {
    return "This file appears to be invalid or corrupted.";
  }

  return message;
}

export default function usePDFDocument(totalPages?: number | null) {
  const [numPages, setNumPages] = useState<number | null>(totalPages ?? null);
  const [loadState, setLoadState] = useState<ReaderLoadState>("loading");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const resolvedPageCount = useMemo(
    () => numPages ?? totalPages ?? null,
    [numPages, totalPages],
  );

  const handleRetry = useCallback(() => {
    setLoadState("loading");
    setLoadError(null);
    setReloadKey((current) => current + 1);
    setNumPages(totalPages ?? null);
  }, [totalPages]);

  const onDocumentLoadSuccess = useCallback(({ numPages: loadedPages }: { numPages: number }) => {
    setNumPages(loadedPages);
    setLoadState("ready");
    setLoadError(null);
  }, []);

  const onDocumentLoadError = useCallback((error: Error) => {
    setLoadState("error");
    setLoadError(formatDocumentError(error.message));
  }, []);

  return {
    numPages,
    resolvedPageCount,
    loadState,
    loadError,
    reloadKey,
    setNumPages,
    handleRetry,
    onDocumentLoadSuccess,
    onDocumentLoadError,
    formatDocumentError,
  };
}
