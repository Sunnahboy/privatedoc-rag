import { useState } from "react";
import { apiClient, RagResponse } from "@/lib/api-client";

export function useRAGQuery() {
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<RagResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // askQuestion can be used as a form submit handler (askQuestion(e))
    // or called programmatically with selected doc ids (askQuestion(undefined, selectedDocIds))
    const askQuestion = async (e?: React.SyntheticEvent, selectedDocIds?: string[]) => {
      if (e && typeof (e as React.SyntheticEvent).preventDefault === "function") e.preventDefault();
      if (!query.trim()) return;

      try {
        setIsLoading(true);
        setError(null);
        setResponse(null); // Clear previous answer

        const docs = selectedDocIds && selectedDocIds.length > 0 ? selectedDocIds : undefined;
        const result = await apiClient.askQuestion(query, docs);
        setResponse(result);

      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to get an answer.");
      } finally {
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