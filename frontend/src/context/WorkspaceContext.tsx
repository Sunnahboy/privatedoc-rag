"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { apiClient, ChatScopeType, ChatSessionSummary } from "@/lib/api-client";

const LAST_SESSION_STORAGE_KEY = "privatedoc.active-chat-session-id";

interface WorkspaceContextValue {
  /** Controls the PDF reader. Independent from the active chat session. */
  activeDocumentId: string | null;
  setActiveDocumentId: (id: string | null) => void;

  /** Controls the Chat panel. Independent from the document being read. */
  activeChatSessionId: string | null;
  setActiveChatSessionId: (id: string | null) => void;

  /** The persisted search-scope for the *active* chat session. */
  chatScope: ChatScopeType;
  setChatScope: (scope: ChatScopeType) => void;

  /** Document ids used when chatScope is SELECTED_DOCUMENTS (or the resolved ids for other scopes). */
  selectedDocumentIds: string[];
  setSelectedDocumentIds: (ids: string[]) => void;

  /** All known chat sessions, used to populate the Chat History sidebar. */
  sessions: ChatSessionSummary[];
  isLoadingSessions: boolean;
  refreshSessions: () => Promise<void>;

  /**
   * Creates a brand new chat session with the given scope/documents,
   * makes it active, and returns its id (or null on failure).
   */
  startNewChat: (scope: ChatScopeType, documentIds: string[]) => Promise<string | null>;

  /**
   * Deletes a chat session (cascades to its messages server-side).
   * Optimistically removes it from the sidebar list; if it was the active
   * session, clears activeChatSessionId so the chat view resets safely.
   */
  deleteSession: (sessionId: string) => Promise<void>;

  /** Whether the Chat History sidebar is visible in Chat Focus mode. */
  isChatSidebarOpen: boolean;
  setIsChatSidebarOpen: (open: boolean) => void;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({
  children,
  initialDocumentId = null,
}: {
  children: ReactNode;
  initialDocumentId?: string | null;
}) {
  const [activeDocumentId, setActiveDocumentId] = useState<string | null>(initialDocumentId);
  const [activeChatSessionId, setActiveChatSessionIdState] = useState<string | null>(null);
  const [chatScope, setChatScope] = useState<ChatScopeType>(
    initialDocumentId ? "THIS_DOCUMENT" : "ALL_DOCUMENTS",
  );
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>(
    initialDocumentId ? [initialDocumentId] : [],
  );
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [isChatSidebarOpen, setIsChatSidebarOpen] = useState(true);

  // Restore the last active chat session on mount (client-only).
  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(LAST_SESSION_STORAGE_KEY);
      if (saved) {
        setActiveChatSessionIdState(saved);
      }
    } catch {
      // Storage can be unavailable in private browsing contexts.
    }
  }, []);

  const setActiveChatSessionId = useCallback((id: string | null) => {
    setActiveChatSessionIdState(id);
    try {
      if (id) {
        window.localStorage.setItem(LAST_SESSION_STORAGE_KEY, id);
      } else {
        window.localStorage.removeItem(LAST_SESSION_STORAGE_KEY);
      }
    } catch {
      // Storage can be unavailable in private browsing contexts.
    }
  }, []);

  const refreshSessions = useCallback(async () => {
    try {
      setIsLoadingSessions(true);
      const list = await apiClient.listChatSessions();
      setSessions(list);
    } catch (err) {
      console.error("Failed to load chat sessions", err);
    } finally {
      setIsLoadingSessions(false);
    }
  }, []);

  useEffect(() => {
    void refreshSessions();
  }, [refreshSessions]);

  const startNewChat = useCallback(
    async (scope: ChatScopeType, documentIds: string[]) => {
      try {
        const session = await apiClient.createChatSession(scope, documentIds);
        setSessions((prev) => [session, ...prev]);
        setActiveChatSessionId(session.id);
        setChatScope(scope);
        setSelectedDocumentIds(documentIds);
        return session.id;
      } catch (err) {
        console.error("Failed to create chat session", err);
        return null;
      }
    },
    [setActiveChatSessionId],
  );

  const deleteSession = useCallback(
    async (sessionId: string) => {
      // Optimistically remove from the sidebar list first.
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (activeChatSessionId === sessionId) {
        setActiveChatSessionId(null);
      }
      try {
        await apiClient.deleteChatSession(sessionId);
      } catch (err) {
        console.error("Failed to delete chat session", err);
        // Re-sync with the server in case the optimistic removal was wrong.
        void refreshSessions();
      }
    },
    [activeChatSessionId, setActiveChatSessionId, refreshSessions],
  );

  const value = useMemo<WorkspaceContextValue>(
    () => ({
      activeDocumentId,
      setActiveDocumentId,
      activeChatSessionId,
      setActiveChatSessionId,
      chatScope,
      setChatScope,
      selectedDocumentIds,
      setSelectedDocumentIds,
      sessions,
      isLoadingSessions,
      refreshSessions,
      startNewChat,
      deleteSession,
      isChatSidebarOpen,
      setIsChatSidebarOpen,
    }),
    [
      activeDocumentId,
      activeChatSessionId,
      setActiveChatSessionId,
      chatScope,
      selectedDocumentIds,
      sessions,
      isLoadingSessions,
      refreshSessions,
      startNewChat,
      deleteSession,
      isChatSidebarOpen,
    ],
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace(): WorkspaceContextValue {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) {
    throw new Error("useWorkspace must be used within a WorkspaceProvider");
  }
  return ctx;
}
