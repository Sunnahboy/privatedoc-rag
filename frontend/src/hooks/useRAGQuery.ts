import { useState, useEffect, useLayoutEffect, useRef } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation"; 
import { apiClient, RagResponse, ChatMessage, StreamChunk, Citation } from "@/lib/api-client";

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

interface UseRAGQueryOptions {
  /**
   * When provided, the chat session is fully controlled by the caller
   * (e.g. WorkspaceContext's activeChatSessionId) instead of being tracked
   * via the URL/localStorage. Pass `null` for "no active session yet".
   */
  controlledSessionId?: string | null;
  /** Called whenever a new session id is created/assigned server-side. */
  onSessionChange?: (sessionId: string | null) => void;
}

// Per-session generation state. Kept OUTSIDE React state so that a
// background stream (for a session that is no longer the active one) can
// keep mutating its own slot without triggering renders for whichever
// session is currently on screen. The active session's slot is mirrored
// into React state via `bumpVersion` so the UI still re-renders when its
// own slot changes.
interface SessionSlot {
  chatHistory: ChatMessage[];
  isLoading: boolean;
  statusMessage: string | null;
  error: string | null;
  response: RagResponse | null;
}

function emptySlot(): SessionSlot {
  return { chatHistory: [], isLoading: false, statusMessage: null, error: null, response: null };
}

// Module-level so it survives across hook remounts within the same tab
// (e.g. navigating away and back) without losing in-flight generations.
const sessionSlots = new Map<string, SessionSlot>();
const NEW_SESSION_KEY = "__pending__";

function getSlot(id: string | null): SessionSlot {
  const key = id ?? NEW_SESSION_KEY;
  let slot = sessionSlots.get(key);
  if (!slot) {
    slot = emptySlot();
    sessionSlots.set(key, slot);
  }
  return slot;
}

export function useRAGQuery(options: UseRAGQueryOptions = {}) {
  const { controlledSessionId, onSessionChange } = options;
  const isControlled = controlledSessionId !== undefined;

  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();
  
  const urlSessionId = searchParams.get("session_id");

  const [query, setQuery] = useState("");

  const [internalSessionId, setInternalSessionId] = useState<string | null>(null);
  const sessionId = isControlled ? controlledSessionId ?? null : internalSessionId;
  const sessionIdRef = useRef<string | null>(null);

  // Keep the ref in sync before the browser paints when an externally
  // controlled session changes. Explicit handoffs also update it immediately
  // below, before their asynchronous state update is rendered.
  useLayoutEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  // Bumps whenever the ACTIVE session's slot is mutated, forcing a
  // re-render so the mirrored fields below reflect the latest values.
  const [, forceRender] = useState(0);
  const rerenderIfActive = (id: string | null) => {
    if ((id ?? NEW_SESSION_KEY) === (sessionIdRef.current ?? NEW_SESSION_KEY)) {
      forceRender((n) => n + 1);
    }
  };

  const activeSlot = getSlot(sessionId);
  const isLoading = activeSlot.isLoading;
  const response = activeSlot.response;
  const error = activeSlot.error;
  const chatHistory = activeSlot.chatHistory;
  const statusMessage = activeSlot.statusMessage;

  const setError = (value: string | null) => {
    getSlot(sessionId).error = value;
    rerenderIfActive(sessionId);
  };

  // Session-scoped setters used by background stream callbacks. `id` is the
  // TARGET session captured at call time (never re-read from a ref), so a
  // callback for a backgrounded session updates only that session's slot -
  // never whatever session happens to be active when the chunk arrives.
  const setLoadingFor = (id: string | null, value: boolean) => {
    getSlot(id).isLoading = value;
    rerenderIfActive(id);
  };
  const setStatusFor = (id: string | null, value: string | null) => {
    getSlot(id).statusMessage = value;
    rerenderIfActive(id);
  };
  const setErrorFor = (id: string | null, value: string | null) => {
    getSlot(id).error = value;
    rerenderIfActive(id);
  };
  const setResponseFor = (id: string | null, value: RagResponse | null) => {
    getSlot(id).response = value;
    rerenderIfActive(id);
  };
  const setHistoryFor = (id: string | null, updater: ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[])) => {
    const slot = getSlot(id);
    slot.chatHistory = typeof updater === "function" ? (updater as (prev: ChatMessage[]) => ChatMessage[])(slot.chatHistory) : updater;
    rerenderIfActive(id);
  };

  // If a session's key changes (e.g. a brand-new chat gets its real id
  // assigned by the server), migrate its in-progress slot across so the
  // background generation keeps mapping to the right session going forward.
  const migrateSlot = (fromId: string | null, toId: string) => {
    const fromKey = fromId ?? NEW_SESSION_KEY;
    if (fromKey === toId) return;
    const slot = sessionSlots.get(fromKey);
    if (slot) {
      sessionSlots.set(toId, slot);
      sessionSlots.delete(fromKey);
    }
  };

  const setSessionId = (next: string | null) => {
    // State updates are asynchronous. Update the ref now so all callbacks
    // that run after `/rag/ask` returns (status, history, and SSE events)
    // target the same slot that the next render will display.
    sessionIdRef.current = next;
    if (isControlled) {
      onSessionChange?.(next);
    } else {
      setInternalSessionId(next);
    }
  };

  // Legacy URL/localStorage-driven session resolution. Skipped entirely
  // when the session is externally controlled (Chat Focus workspace).
  useEffect(() => {
    if (isControlled) return;

    if (urlSessionId) {
      setInternalSessionId(urlSessionId);
      localStorage.setItem("rag_last_session_id", urlSessionId);
    } else {
      const savedId = localStorage.getItem("rag_last_session_id");
      if (savedId) {
        setInternalSessionId(savedId);
        const newParams = new URLSearchParams(searchParams.toString());
        newParams.set("session_id", savedId);
        router.replace(`${pathname}?${newParams.toString()}`);
      }
    }
  }, [isControlled, urlSessionId, pathname, router, searchParams]);

  useEffect(() => {
    const abortController = new AbortController();

    if (sessionId) {
      // Only fetch from the DB if we don't already have a live/cached
      // slot for this session (e.g. it's not currently generating in the
      // background) - otherwise switching back to a session would stomp
      // on tokens that streamed in while it was backgrounded.
      const existing = sessionSlots.get(sessionId);
      if (!existing || !existing.isLoading) {
        loadHistory(sessionId, abortController.signal);
      } else {
        rerenderIfActive(sessionId);
      }
    }

    return () => {
      abortController.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  const loadHistory = async (id: string, signal?: AbortSignal) => {
    try {
      const history = await apiClient.getChatHistory(id);
      setHistoryFor(id, history);

      const lastMessage = history[history.length - 1];

      if (lastMessage && lastMessage.role === "assistant" && ["queued", "processing"].includes(lastMessage.status || "")) {
          setLoadingFor(id, true);
          setStatusFor(id, "Reconnecting to stream...");

          // THE FIX: The backend always replays the entire buffered history
          // from scratch on every connect/reconnect. `streamedAnswer` is
          // reset in `onReplayStart` (fired on every EventSource open,
          // including native reconnects) so a resumed connection
          // deterministically rebuilds the exact UI state - current status
          // message and/or partial text - instead of ever rendering a blank
          // bubble.
          let streamedAnswer = "";

          // Promise blocks here until the stream finishes naturally. Note
          // every callback below targets `id` (the captured session id),
          // NOT sessionIdRef.current - so this keeps updating the correct
          // session's slot even if the user switches away mid-stream.
          await apiClient.streamChatResponse(
            lastMessage.id,
            (chunk: StreamChunk) => {
               if (chunk.type === "status") {
                  setStatusFor(id, chunk.message);
               } else if (chunk.type === "token") {
                  streamedAnswer += chunk.content;
                  // THE FIX: Do not wipe the status message until the LLM actually outputs a visible word!
                  if (chunk.content.trim().length > 0) {
                      setStatusFor(id, null);
                  }

                  setHistoryFor(id, (prev) => prev.map((msg) => 
                    msg.id === lastMessage.id ? { ...msg, content: streamedAnswer, status: "processing" } : msg
                  ));
               } else if (chunk.type === "done") {
                  apiClient.getChatHistory(id).then((finalHistory) => {
                      setHistoryFor(id, finalHistory);
                      setLoadingFor(id, false);
                  });
               } else if (chunk.type === "error") {
                  setErrorFor(id, chunk.error);
                  setLoadingFor(id, false);
               }
            },
            signal,
            () => {
               // Reset accumulator right before the replayed events start.
               streamedAnswer = "";
               setStatusFor(id, "Reconnecting to stream...");
               setHistoryFor(id, (prev) => prev.map((msg) =>
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
    documentIds: string[] = [],
    explicitQuery?: string,
    signal?: AbortSignal,
  ): Promise<RagResponse | null> => {
    if (e && typeof (e as React.SyntheticEvent).preventDefault === "function") e.preventDefault();

    const q = typeof explicitQuery === 'string' ? explicitQuery : query;
    if (!q || !q.trim()) return null;

    let targetSessionId: string | null = sessionIdRef.current;

    try {
      const currentSessionId = sessionIdRef.current;
      targetSessionId = currentSessionId;

      setLoadingFor(currentSessionId, true);
      setErrorFor(currentSessionId, null);
      setResponseFor(currentSessionId, null);
      setStatusFor(currentSessionId, "Queuing job...");

      const { session_id, user_message_id, assistant_message_id } = await apiClient.submitChatJob(
        q,
        documentIds,
        currentSessionId,
        signal,
      );

      // The slot was keyed by `currentSessionId` (possibly the "no session
      // yet" bucket). Now that the server has assigned a real session id,
      // migrate that in-progress slot across so subsequent chunks (keyed
      // by `targetSessionId` below) land in the right place, and so
      // switching to this brand-new chat later finds its live state.
      migrateSlot(currentSessionId, session_id);
      targetSessionId = session_id;

      if (!currentSessionId) {
        setSessionId(session_id);
        if (!isControlled) {
          localStorage.setItem("rag_last_session_id", session_id);
          const newParams = new URLSearchParams(searchParams.toString());
          newParams.set("session_id", session_id);
          router.replace(`${pathname}?${newParams.toString()}`);
          
        }
      }

      setHistoryFor(targetSessionId, (prev) => [
        ...prev,
        { id: user_message_id, session_id: session_id, role: "user", content: q, citations: [], created_at: new Date().toISOString() },
        { id: assistant_message_id, session_id: session_id, role: "assistant", content: "", citations: [], status: "queued", created_at: new Date().toISOString() }
      ]);

      setStatusFor(targetSessionId, "Waiting for worker...");
      let streamedAnswer = "";
      let streamedCitations: Citation[] = [];

      // Promise blocks here until the stream finishes naturally, keeping UI
      // alive. Every callback below targets `targetSessionId` (captured
      // above), so it keeps updating the correct session's slot in the
      // background even if the user switches to a different chat mid-flight.
      await apiClient.streamChatResponse(
        assistant_message_id,
        (chunk: StreamChunk) => {
          if (chunk.type === "status") {
             setStatusFor(targetSessionId, chunk.message);
          }
          else if (chunk.type === "token") {
            // THE FIX: Do not wipe the status message until the LLM actually outputs a visible word!
            if (chunk.content.trim().length > 0) {
                setStatusFor(targetSessionId, null);
            }
            
            streamedAnswer += chunk.content;
            setHistoryFor(targetSessionId, (prev) => prev.map((msg) => 
              msg.id === assistant_message_id ? { ...msg, content: streamedAnswer, status: "processing" } : msg
            ));
          }
          else if (chunk.type === "done") {
            streamedCitations = chunk.citations || [];
            setHistoryFor(targetSessionId, (prev) => prev.map((msg) => 
              msg.id === assistant_message_id ? { ...msg, content: streamedAnswer, citations: streamedCitations, status: "completed" } : msg
            ));
            setResponseFor(targetSessionId, { session_id, answer: streamedAnswer, citations: streamedCitations });
          }
          else if (chunk.type === "error") {
             setErrorFor(targetSessionId, chunk.error);
          }
        },
        signal,
        () => {
          // THE FIX: Same replay-reset safety net as the reconnect path -
          // guards against the browser's native EventSource auto-reconnect
          // firing mid-generation and re-appending already-streamed tokens.
          streamedAnswer = "";
          setStatusFor(targetSessionId, "Reconnecting to stream...");
          setHistoryFor(targetSessionId, (prev) => prev.map((msg) =>
            msg.id === assistant_message_id ? { ...msg, content: "" } : msg
          ));
        }
      );

      return { session_id, answer: streamedAnswer, citations: streamedCitations };

    } catch (err: unknown) {
      if (isAbortError(err)) return null;
      setErrorFor(targetSessionId, err instanceof Error ? err.message : "Failed to get an answer.");
      return null;
    } finally {
      setLoadingFor(targetSessionId, false);
      setStatusFor(targetSessionId, null);
      setQuery("");
    }
  };

  const handleEditMessage = async (messageId: string, newText: string, selectedDocIds?: string[]) => {
    const activeSessionId = sessionIdRef.current ?? sessionId;
    if (!activeSessionId || !newText.trim()) return;

    try {
      await apiClient.truncateChatHistory(activeSessionId, messageId);
      setHistoryFor(activeSessionId, (prev) => {
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
    // Reset the "pending new chat" bucket so a stale draft/loading state
    // doesn't bleed into the next brand-new chat.
    sessionSlots.set(NEW_SESSION_KEY, emptySlot());
    setSessionId(null);
    rerenderIfActive(null);

    if (!isControlled) {
      localStorage.removeItem("rag_last_session_id");
      const newParams = new URLSearchParams(searchParams.toString());
      newParams.delete("session_id");
      router.replace(`${pathname}?${newParams.toString()}`);
      
    }
  };

  return { query, setQuery, isLoading, response, error, setError, askQuestion, handleEditMessage, clearChat, chatHistory, sessionId, statusMessage };
}
