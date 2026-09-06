"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { useWorkspace } from "@/context/WorkspaceContext";
import { useDocuments } from "@/hooks/useDocuments";
import type { ChatSessionSummary } from "@/lib/api-client";

interface ChatHistorySidebarProps {
  /** The document currently open in the reader, used to default new chats. */
  activeDocumentId?: string | null;
  className?: string;
}

interface SidebarGroup {
  key: string;
  label: string;
  sessions: ChatSessionSummary[];
}

function groupSessions(sessions: ChatSessionSummary[], documentTitleFor: (id: string) => string): SidebarGroup[] {
  const groups = new Map<string, SidebarGroup>();

  for (const session of sessions) {
    let key: string;
    let label: string;

    if (session.scope_type === "ALL_DOCUMENTS" || session.document_ids.length === 0) {
      key = "__all__";
      label = "All Documents";
    } else if (session.document_ids.length === 1) {
      key = session.document_ids[0];
      label = documentTitleFor(session.document_ids[0]);
    } else {
      key = `selected:${session.document_ids.slice().sort().join(",")}`;
      label = `Selected (${session.document_ids.length} documents)`;
    }

    const existing = groups.get(key);
    if (existing) {
      existing.sessions.push(session);
    } else {
      groups.set(key, { key, label, sessions: [session] });
    }
  }

  // "All Documents" last, everything else alphabetically by label.
  return Array.from(groups.values()).sort((a, b) => {
    if (a.key === "__all__") return 1;
    if (b.key === "__all__") return -1;
    return a.label.localeCompare(b.label);
  });
}

interface ChatSessionMenuProps {
  isOpen: boolean;
  onOpen: () => void;
  onClose: () => void;
  onRename: () => void;
  onPin: () => void;
  onDelete: () => void;
}

/** The vertical 3-dot trigger + floating menu for a single chat row's actions. */
function ChatSessionMenu({ isOpen, onOpen, onClose, onRename, onPin, onDelete }: ChatSessionMenuProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;

    function handlePointerDown(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        onClose();
      }
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  return (
    <div ref={containerRef} className="relative shrink-0">
      <button
        type="button"
        onClick={(event) => {
          event.stopPropagation();
          isOpen ? onClose() : onOpen();
        }}
        aria-label="Chat options"
        aria-haspopup="menu"
        aria-expanded={isOpen}
        title="Chat options"
        className={`flex items-center justify-center rounded-md p-1 text-on-surface-variant transition-opacity hover:bg-surface-container-highest hover:text-on-surface focus-visible:opacity-100 focus-visible:outline-none ${
          isOpen ? "opacity-100" : "opacity-0 group-hover:opacity-100"
        }`}
      >
        <span className="material-symbols-outlined text-[16px]" aria-hidden="true">
          more_vert
        </span>
      </button>

      {isOpen && (
        <div
          role="menu"
          className="absolute right-0 top-full z-50 mt-1 w-40 overflow-hidden rounded-lg border border-outline-variant/20 bg-surface-elevated py-1 shadow-lg"
        >
          <button
            type="button"
            role="menuitem"
            onClick={(event) => {
              event.stopPropagation();
              onClose();
              onRename();
            }}
            className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm text-on-surface transition-colors hover:bg-surface-container"
          >
            <span aria-hidden="true">✏️</span>
            Rename
          </button>
          <button
            type="button"
            role="menuitem"
            onClick={(event) => {
              event.stopPropagation();
              onClose();
              onPin();
            }}
            className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm text-on-surface transition-colors hover:bg-surface-container"
          >
            <span aria-hidden="true">📌</span>
            Pin chat
          </button>
          <button
            type="button"
            role="menuitem"
            onClick={(event) => {
              event.stopPropagation();
              onClose();
              onDelete();
            }}
            className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm text-error transition-colors hover:bg-error/10"
          >
            <span aria-hidden="true">🗑️</span>
            Delete
          </button>
        </div>
      )}
    </div>
  );
}

export function ChatHistorySidebar({ activeDocumentId, className }: ChatHistorySidebarProps) {
  const {
    sessions,
    isLoadingSessions,
    activeChatSessionId,
    setActiveChatSessionId,
    startNewChat,
    deleteSession,
    setIsChatSidebarOpen,
  } = useWorkspace();
  const { documents } = useDocuments({ autoFetch: true });
  const [openMenuSessionId, setOpenMenuSessionId] = useState<string | null>(null);

  const documentTitleFor = useMemo(() => {
    const byId = new Map(documents.map((doc) => [doc.document_id, doc.original_filename]));
    return (id: string) => byId.get(id) ?? "Unknown document";
  }, [documents]);

  const groups = useMemo(() => groupSessions(sessions, documentTitleFor), [sessions, documentTitleFor]);

  const handleNewChat = async () => {
    if (activeDocumentId) {
      await startNewChat("THIS_DOCUMENT", [activeDocumentId]);
    } else {
      await startNewChat("ALL_DOCUMENTS", []);
    }
  };

  return (
    <nav
      aria-label="Chat history"
      className={`flex h-full min-h-0 flex-col overflow-hidden bg-surface ${className ?? ""}`}
    >
      <div className="flex shrink-0 items-center gap-2 border-b border-outline-variant/20 p-3">
        <button
          type="button"
          onClick={() => void handleNewChat()}
          className="flex flex-1 items-center justify-center gap-2 rounded-lg border border-outline-variant/30 bg-surface-elevated px-3 py-2 text-sm font-medium text-on-surface shadow-sm transition-colors hover:bg-surface-container focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
        >
          <span className="material-symbols-outlined text-[18px]" aria-hidden="true">
            add
          </span>
          New Chat
        </button>
        <button
          type="button"
          onClick={() => setIsChatSidebarOpen(false)}
          aria-label="Collapse chat sidebar"
          title="Collapse sidebar"
          className="flex shrink-0 items-center justify-center rounded-lg bg-transparent p-2 text-on-surface-variant transition-colors hover:bg-surface-container hover:text-on-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
        >
          <span className="material-symbols-outlined text-[18px]" aria-hidden="true">
            dock_to_right
          </span>
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        <p className="mb-2 px-1 text-xs font-semibold uppercase tracking-[0.2em] text-on-surface-variant">
          Chats
        </p>

        {isLoadingSessions && sessions.length === 0 ? (
          <p className="px-1 text-xs text-on-surface-variant">Loading…</p>
        ) : sessions.length === 0 ? (
          <p className="px-1 text-xs italic text-on-surface-variant/70">
            No conversations yet. Start a new chat to begin.
          </p>
        ) : (
          <div className="flex flex-col gap-4">
            {groups.map((group) => (
              <div key={group.key}>
                <p className="mb-1 truncate px-1 text-xs font-medium text-on-surface-variant/80">
                  {group.label}
                </p>
                <div className="flex flex-col gap-0.5">
                  {group.sessions.map((session) => {
                    const isActive = session.id === activeChatSessionId;
                    return (
                      <div
                        key={session.id}
                        className={`group relative flex items-center gap-1 rounded-md pr-1 transition-colors ${
                          isActive
                            ? "bg-primary/10"
                            : "hover:bg-surface-container-low"
                        }`}
                      >
                        <button
                          type="button"
                          onClick={() => setActiveChatSessionId(session.id)}
                          aria-current={isActive ? "true" : undefined}
                          className={`min-w-0 flex-1 truncate rounded-md px-2 py-1.5 text-left text-sm transition-colors ${
                            isActive
                              ? "font-medium text-primary"
                              : "text-on-surface/85 group-hover:text-primary"
                          }`}
                        >
                          {session.title?.trim() || "New Chat"}
                        </button>
                        <ChatSessionMenu
                          isOpen={openMenuSessionId === session.id}
                          onOpen={() => setOpenMenuSessionId(session.id)}
                          onClose={() => setOpenMenuSessionId((current) => (current === session.id ? null : current))}
                          onRename={() => console.log("[ChatHistorySidebar] Rename chat (placeholder):", session.id)}
                          onPin={() => console.log("[ChatHistorySidebar] Pin chat (placeholder):", session.id)}
                          onDelete={() => void deleteSession(session.id)}
                        />
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </nav>
  );
}

export default ChatHistorySidebar;
