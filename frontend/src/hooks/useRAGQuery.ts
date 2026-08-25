import { useState, useEffect, useRef } from "react";
import { apiClient, RagResponse, ChatMessage, StreamChunk, Citation } from "@/lib/api-client";

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
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Use a mutable ref to track the current sessionId during asynchronous stream loops
  const sessionIdRef = useRef<string | null>(null);

  // Sync ref with state whenever sessionId updates
  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  // Load session from localStorage on mount
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
      localStorage.removeItem("rag_session_id");
      setSessionId(null);
    }
  };

  const askQuestion = async (
    e?: React.SyntheticEvent,
    selectedDocIds?: string[],
    explicitQuery?: string,
    signal?: AbortSignal,
  ): Promise<RagResponse | null> => {
    if (e && typeof (e as React.SyntheticEvent).preventDefault === "function") e.preventDefault();

    const q = typeof explicitQuery === 'string' ? explicitQuery : query;
    if (!q || !q.trim()) return null;

    try {
      setIsLoading(true);
      setError(null);
      setResponse(null); 
      setStatusMessage("Initializing query...");

      const docs = selectedDocIds && selectedDocIds.length > 0 ? selectedDocIds : undefined;
      const tempAssistantMsgId = `temp-asst-${Date.now()}`;

      // Capture snapshot of current session ID securely from the ref
      const currentSessionId = sessionIdRef.current;

      setChatHistory((prev) => [
        ...prev,
        { 
          id: tempAssistantMsgId, 
          session_id: currentSessionId || "", 
          role: "assistant", 
          content: "", 
          citations: [], 
          created_at: new Date().toISOString() 
        }
      ]);

      let finalSessionId = currentSessionId;
      let streamedAnswer = "";
      let streamedCitations: Citation[] = [];
      let finalResponse: RagResponse | null = null;
      let hasClearedStatusForStream = false;

      await apiClient.askQuestionStream(
        q,
        docs,
        currentSessionId,
        (chunk: StreamChunk) => {
          if (chunk.type === "session") {
            finalSessionId = chunk.session_id;
            setSessionId(chunk.session_id);
            localStorage.setItem("rag_session_id", chunk.session_id);
          }
          else if (chunk.type === "status") {
            setStatusMessage((prev) => (prev !== chunk.message ? chunk.message : prev));
          }
          else if (chunk.type === "token") {
            if (!hasClearedStatusForStream) {
              hasClearedStatusForStream = true;
              setStatusMessage(null);
            }
            
            streamedAnswer += chunk.content;
            
            setChatHistory((prev) => prev.map((msg) => 
              msg.id === tempAssistantMsgId 
                ? { ...msg, content: streamedAnswer } 
                : msg
            ));
          } 
          else if (chunk.type === "done") {
            setStatusMessage(null);
            streamedCitations = chunk.citations;
            
            setChatHistory((prev) => prev.map((msg) => 
              msg.id === tempAssistantMsgId 
                ? { ...msg, citations: streamedCitations } 
                : msg
            ));

            if (finalSessionId) {
                finalResponse = {
                  session_id: finalSessionId,
                  answer: streamedAnswer,
                  citations: streamedCitations
                };
                setResponse(finalResponse);
            }
          }
          else if (chunk.type === "error") {
             setError(chunk.error);
          }
        },
        signal
      );

      if (finalSessionId) {
        await loadHistory(finalSessionId);
      }
      return finalResponse;

    } catch (err: unknown) {
      if (isAbortError(err)) {
        return null;
      }
      setError(err instanceof Error ? err.message : "Failed to get an answer.");
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = () => {
    setQuery("");
    setResponse(null);
    setError(null);
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
    chatHistory,
    sessionId,
    statusMessage
  };
}
