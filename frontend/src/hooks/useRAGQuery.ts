import { useState,useEffect } from "react";
import { apiClient, RagResponse, ChatMessage } from "@/lib/api-client";

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

export function useRAGQuery() {
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<RagResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);

  //Load session from localStorage on mount
  useEffect(() => {
    const savedSessionId = localStorage.getItem("rag_session_id");
    if (savedSessionId) {
      setSessionId(savedSessionId);
      loadHistory(savedSessionId);
    }
  }, []);

  const loadHistory = async (id: string) => {
    try {
      const history = await apiClient.getChatHistory(id);
      setChatHistory(history);
    } catch (err) {
      console.error("Failed to load chat history:", err);
      // If the session is invalid/not found, clear it
      localStorage.removeItem("rag_session_id");
      setSessionId(null);
    }
  };

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
        const result = await apiClient.askQuestion(q, docs, sessionId, signal);

        // If the backend gave us a new session ID, save it to state & localStorage
      if (result.session_id && result.session_id !== sessionId) {
        setSessionId(result.session_id);
        localStorage.setItem("rag_session_id", result.session_id);
      }
      setResponse(result);
      //Refresh the chat history to include the new Q&A
      if (result.session_id) {
          await loadHistory(result.session_id);
      }
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
    //Clear session state completely 
    setSessionId(null);
    setChatHistory([]);
    localStorage.removeItem("rag_session_id");
  };

  return {
    query,
    setQuery,
    isLoading,
    response,
    error,
    askQuestion,
    clearChat,
    //Expose history to the UI
    chatHistory,
    sessionId
  };
}