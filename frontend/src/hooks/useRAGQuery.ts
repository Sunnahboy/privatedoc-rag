import { useState } from "react";
import { apiClient, RagResponse } from "@/lib/api-client";

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

export function useRAGQuery() {
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<RagResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // askQuestion can be used as a form submit handler (askQuestion(e))
    // or called programmatically with selected doc ids (askQuestion(undefined, selectedDocIds))
    // askQuestion: optional event, optional selectedDocIds, optional explicitQuery override
    const askQuestion = async (
      e?: React.SyntheticEvent,
      selectedDocIds?: string[],
      explicitQuery?: string,
      signal?: AbortSignal,
    ) => {
      if (e && typeof (e as React.SyntheticEvent).preventDefault === "function") e.preventDefault();

      const q = typeof explicitQuery === 'string' ? explicitQuery : query;
      if (!q || !q.trim()) return null;

      try {
        setIsLoading(true);
        setError(null);
        setResponse(null); // Clear previous answer

        const docs = selectedDocIds && selectedDocIds.length > 0 ? selectedDocIds : undefined;
        const result = await apiClient.askQuestion(q, docs, signal);
        setResponse(result);
        return result;

      } catch (err: unknown) {
        // If the request was aborted, don't treat as an error to show to the user
        if (isAbortError(err)) {
          // Keep error state untouched for aborts
          return null;
        }
        setError(err instanceof Error ? err.message : "Failed to get an answer.");
        return null;
      } finally {
        // Always unlock the input even if network call fails or throws.
        setIsLoading(false);
      }
    };

  const clearChat = () => {
    setQuery("");
    setResponse(null);
    setError(null);
  };

  return {
    query,
    setQuery,
    isLoading,
    response,
    error,
    askQuestion,
    clearChat,
  };
}