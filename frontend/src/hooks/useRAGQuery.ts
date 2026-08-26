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

  // Load persisted session and chat history from localStorage on mount.
  useEffect(() => {
    const savedSessionId = localStorage.getItem("rag_session_id");
    const savedHistory = localStorage.getItem("rag_chat_history");

    if (savedSessionId) {
      setSessionId(savedSessionId);
    }

    if (savedHistory) {
      try {
        const parsedHistory = JSON.parse(savedHistory) as ChatMessage[];
        if (Array.isArray(parsedHistory)) {
          setChatHistory(parsedHistory);
        }
      } catch (err) {
        console.error("Failed to parse cached chat history:", err);
        localStorage.removeItem("rag_chat_history");
      }
    }

    if (savedSessionId) {
      loadHistory(savedSessionId);
    }
  }, []);

  useEffect(() => {
    const serialized = JSON.stringify(chatHistory);
    const stored = localStorage.getItem("rag_chat_history");

    if (chatHistory.length > 0) {
      if (stored !== serialized) {
        localStorage.setItem("rag_chat_history", serialized);
      }
      return;
    }

    if (stored) {
      localStorage.removeItem("rag_chat_history");
    }
  }, [chatHistory]);

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
      let lastUpdateTime = 0;

      await apiClient.askQuestionStream(
        q,
        docs,
        sessionId,
        (chunk: StreamChunk) => {
          if (chunk.type === "session") {
            finalSessionId = chunk.session_id;
            setSessionId(chunk.session_id);
            localStorage.setItem("rag_session_id", chunk.session_id);
          } 
          else if (chunk.type === "status") {
             setStatusMessage(chunk.message);
          }
          else if (chunk.type === "token") {
            setStatusMessage(null);
            streamedAnswer += chunk.content;
            
            // THROTTLE STATE UPDATES TO ONCE EVERY 50ms
            const now = Date.now();
            if (now - lastUpdateTime > 50) {
                setChatHistory((prev) => prev.map((msg) => 
                  msg.id === tempAssistantMsgId 
                    ? { ...msg, content: streamedAnswer } 
                    : msg
                ));
                lastUpdateTime = now;
            }
          } 
          else if (chunk.type === "done") {
            streamedCitations = chunk.citations;
            
            // FINAL FLUSH: Guarantee the final state is fully updated when done
            setChatHistory((prev) => prev.map((msg) => 
              msg.id === tempAssistantMsgId 
                ? { ...msg, content: streamedAnswer, citations: streamedCitations } 
                : msg
            ));

            if (finalSessionId) {
                setResponse({
                    session_id: finalSessionId,
                    answer: streamedAnswer,
                    citations: streamedCitations
                });
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

  const handleEditMessage = async (messageId: string, newText: string, selectedDocIds?: string[]) => {
    const activeSessionId = sessionIdRef.current ?? sessionId;
    if (!activeSessionId || !newText.trim()) return;

    try {
      // 1. Only call the backend DELETE if it is a real database UUID, 
      // skipping temporary optimistic IDs to prevent 404 errors.
      if (!messageId.startsWith("temp-")) {
        await apiClient.truncateChatHistory(activeSessionId, messageId);
      }

      // 2. Optimistically slice the UI state
      setChatHistory((prev) => {
        const index = prev.findIndex((message) => message.id === messageId);
        return index !== -1 ? prev.slice(0, index) : prev;
      });

      // 3. Re-trigger the generation
      await askQuestion(undefined, selectedDocIds, newText);
    } catch (err) {
      console.error("Failed to edit message:", err);
    }
  };

  const clearChat = () => {
    setQuery("");
    setResponse(null);
    setError(null);
    setSessionId(null);
    setChatHistory([]);
    localStorage.removeItem("rag_session_id");
    localStorage.removeItem("rag_chat_history");
  };

  return {
    query,
    setQuery,
    isLoading,
    response,
    error,
    askQuestion,
    handleEditMessage,
    clearChat,
    chatHistory,
    sessionId,
    statusMessage
  };
}
