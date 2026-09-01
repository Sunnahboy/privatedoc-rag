import { useState, useEffect, useRef } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation"; 
import { apiClient, RagResponse, ChatMessage, StreamChunk, Citation } from "@/lib/api-client";

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

export function useRAGQuery() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();
  
  const urlSessionId = searchParams.get("session_id");

  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<RagResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const sessionIdRef = useRef<string | null>(null);

  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  useEffect(() => {
    if (urlSessionId) {
      setSessionId(urlSessionId);
      localStorage.setItem("rag_last_session_id", urlSessionId);
    } else {
      const savedId = localStorage.getItem("rag_last_session_id");
      if (savedId) {
        setSessionId(savedId);
        const newParams = new URLSearchParams(searchParams.toString());
        newParams.set("session_id", savedId);
        router.replace(`${pathname}?${newParams.toString()}`);
      }
    }
  }, [urlSessionId, pathname, router, searchParams]);

  useEffect(() => {
    const abortController = new AbortController();

    if (sessionId) {
      loadHistory(sessionId, abortController.signal);
    } else {
      setChatHistory([]);
    }

    return () => {
      abortController.abort();
    };
  }, [sessionId]);

  const loadHistory = async (id: string, signal?: AbortSignal) => {
    try {
      const history = await apiClient.getChatHistory(id);
      setChatHistory(history);

      const lastMessage = history[history.length - 1];

      if (lastMessage && lastMessage.role === "assistant" && ["queued", "processing"].includes(lastMessage.status || "")) {
          setIsLoading(true);
          setStatusMessage("Reconnecting to stream...");

          // THE FIX: The backend always replays the entire buffered history
          // from scratch on every connect/reconnect. `streamedAnswer` is
          // reset in `onReplayStart` (fired on every EventSource open,
          // including native reconnects) so a resumed connection
          // deterministically rebuilds the exact UI state - current status
          // message and/or partial text - instead of ever rendering a blank
          // bubble.
          let streamedAnswer = "";

          // Promise blocks here until the stream finishes naturally
          await apiClient.streamChatResponse(
            lastMessage.id,
            (chunk: StreamChunk) => {
               if (chunk.type === "status") {
                  setStatusMessage(chunk.message);
               } else if (chunk.type === "token") {
                  streamedAnswer += chunk.content;
                  // THE FIX: Do not wipe the status message until the LLM actually outputs a visible word!
                  if (chunk.content.trim().length > 0) {
                      setStatusMessage(null);
                  }

                  setChatHistory((prev) => prev.map((msg) => 
                    msg.id === lastMessage.id ? { ...msg, content: streamedAnswer, status: "processing" } : msg
                  ));
               } else if (chunk.type === "done") {
                  apiClient.getChatHistory(id).then((finalHistory) => {
                      setChatHistory(finalHistory);
                      setIsLoading(false);
                  });
               } else if (chunk.type === "error") {
                  setError(chunk.error);
                  setIsLoading(false);
               }
            },
            signal,
            () => {
               // Reset accumulator right before the replayed events start.
               streamedAnswer = "";
               setStatusMessage("Reconnecting to stream...");
               setChatHistory((prev) => prev.map((msg) =>
                 msg.id === lastMessage.id ? { ...msg, content: "" } : msg
               ));
            }
          );
      }
    } catch (err) {
      if (isAbortError(err)) return;
      console.error("Failed to load chat history:", err);
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
      setStatusMessage("Queuing job...");

      const docId = selectedDocIds && selectedDocIds.length > 0 ? selectedDocIds[0] : undefined;
      const currentSessionId = sessionIdRef.current;
      
      const { session_id, user_message_id, assistant_message_id } = await apiClient.submitChatJob(
        q,
        docId,
        currentSessionId
      );

      if (!currentSessionId) {
        setSessionId(session_id);
        localStorage.setItem("rag_last_session_id", session_id);
        const newParams = new URLSearchParams(searchParams.toString());
        newParams.set("session_id", session_id);
        router.replace(`${pathname}?${newParams.toString()}`);
      }

      setChatHistory((prev) => [
        ...prev,
        { id: user_message_id, session_id: currentSessionId || session_id, role: "user", content: q, citations: [], created_at: new Date().toISOString() },
        { id: assistant_message_id, session_id: currentSessionId || session_id, role: "assistant", content: "", citations: [], status: "queued", created_at: new Date().toISOString() }
      ]);

      setStatusMessage("Waiting for worker...");
      let streamedAnswer = "";
      let streamedCitations: Citation[] = [];

      // Promise blocks here until the stream finishes naturally, keeping UI alive
      await apiClient.streamChatResponse(
        assistant_message_id,
        (chunk: StreamChunk) => {
          if (chunk.type === "status") {
             setStatusMessage(chunk.message);
          }
          else if (chunk.type === "token") {
            // THE FIX: Do not wipe the status message until the LLM actually outputs a visible word!
            if (chunk.content.trim().length > 0) {
                setStatusMessage(null);
            }
            
            streamedAnswer += chunk.content;
            setChatHistory((prev) => prev.map((msg) => 
              msg.id === assistant_message_id ? { ...msg, content: streamedAnswer, status: "processing" } : msg
            ));
          }
          else if (chunk.type === "done") {
            streamedCitations = chunk.citations || [];
            setChatHistory((prev) => prev.map((msg) => 
              msg.id === assistant_message_id ? { ...msg, content: streamedAnswer, citations: streamedCitations, status: "completed" } : msg
            ));
            if (session_id) {
                setResponse({ session_id, answer: streamedAnswer, citations: streamedCitations });
            }
          }
          else if (chunk.type === "error") {
             setError(chunk.error);
          }
        },
        signal,
        () => {
          // THE FIX: Same replay-reset safety net as the reconnect path -
          // guards against the browser's native EventSource auto-reconnect
          // firing mid-generation and re-appending already-streamed tokens.
          streamedAnswer = "";
          setStatusMessage("Reconnecting to stream...");
          setChatHistory((prev) => prev.map((msg) =>
            msg.id === assistant_message_id ? { ...msg, content: "" } : msg
          ));
        }
      );

      return { session_id, answer: streamedAnswer, citations: streamedCitations };

    } catch (err: unknown) {
      if (isAbortError(err)) return null;
      setError(err instanceof Error ? err.message : "Failed to get an answer.");
      return null;
    } finally {
      setIsLoading(false);
      setQuery("");
      setStatusMessage(null);
    }
  };

  const handleEditMessage = async (messageId: string, newText: string, selectedDocIds?: string[]) => {
    const activeSessionId = sessionIdRef.current ?? sessionId;
    if (!activeSessionId || !newText.trim()) return;

    try {
      await apiClient.truncateChatHistory(activeSessionId, messageId);
      setChatHistory((prev) => {
        const index = prev.findIndex((message) => message.id === messageId);
        return index !== -1 ? prev.slice(0, index) : prev;
      });
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
    setStatusMessage(null);
    
    localStorage.removeItem("rag_last_session_id");
    const newParams = new URLSearchParams(searchParams.toString());
    newParams.delete("session_id");
    router.replace(`${pathname}?${newParams.toString()}`);
  };

  return { query, setQuery, isLoading, response, error, askQuestion, handleEditMessage, clearChat, chatHistory, sessionId, statusMessage };
}