"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { useWorkspace } from "@/context/WorkspaceContext";
import { useDocuments } from "@/hooks/useDocuments";
import { useRAGQuery } from "@/hooks/useRAGQuery";
import { normalizeDocumentStatus, type ChatScopeType } from "@/lib/api-client";

interface RagChatProps {
  documentId?: string;
  currentPage?: number;
  /** Jumps the PDF viewer to a citation's source page (deep-linking). */
  onNavigateToPage?: (page: number, citationText?: string) => void;
  selectedText?: string | null;
  showDocumentSelector?: boolean;
  isExpanded?: boolean;
  chatFocus?: boolean;
  onToggleExpanded?: () => void;
  className?: string;
  /**
   * When true, the chat session, its search scope, and document selection
   * are all sourced from WorkspaceContext instead of local component state.
   * Used by the Chat Focus workspace so switching documents/sessions in the
   * sidebar doesn't reset an in-flight conversation.
   */
  useWorkspaceScope?: boolean;
  /** Whether the Chat History sidebar is currently visible (Chat Focus only). */
  isChatSidebarOpen?: boolean;
  /** Reopens the Chat History sidebar; renders a header toggle when provided and closed. */
  onOpenChatSidebar?: () => void;
}

const COMPOSER_MAX_HEIGHT = 180;
const COLLAPSE_THRESHOLD = 950;
type SearchScope = "current" | "selected" | "all";

const SCOPE_TO_UI: Record<ChatScopeType, SearchScope> = {
  THIS_DOCUMENT: "current",
  SELECTED_DOCUMENTS: "selected",
  ALL_DOCUMENTS: "all",
};
const UI_TO_SCOPE: Record<SearchScope, ChatScopeType> = {
  current: "THIS_DOCUMENT",
  selected: "SELECTED_DOCUMENTS",
  all: "ALL_DOCUMENTS",
};

function formatMessageTime(createdAt?: string) {
  if (!createdAt) {
    return "";
  }
  return new Date(createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function RagChat({
  documentId,
  currentPage,
  onNavigateToPage,
  selectedText,
  showDocumentSelector = true,
  isExpanded = false,
  chatFocus = false,
  onToggleExpanded,
  className,
  useWorkspaceScope = false,
  isChatSidebarOpen = true,
  onOpenChatSidebar,
}: RagChatProps) {
  // Workspace context is only consulted when this chat is scope-controlled
  // (Chat Focus). Reading it unconditionally is safe because the provider
  // wraps the whole workspace page.
  const workspace = useWorkspace();

  const {
    activeChatSessionId,
    setActiveChatSessionId,
    chatScope: workspaceScope,
    setChatScope: setWorkspaceScope,
    selectedDocumentIds: workspaceSelectedIds,
    setSelectedDocumentIds: setWorkspaceSelectedIds,
  } = workspace;

  // THE FIX: We pull statusMessage directly from the hook now
  const {
    query,
    setQuery,
    isLoading,
    askQuestion,
    error,
    setError,
    clearChat,
    chatHistory,
    handleEditMessage,
    statusMessage,
  } = useRAGQuery(
    useWorkspaceScope
      ? { controlledSessionId: activeChatSessionId, onSessionChange: setActiveChatSessionId }
      : {},
  );
  const { documents, isLoading: docsLoading, fetchDocuments } = useDocuments({ autoFetch: showDocumentSelector });

  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(documentId ?? null);
  const [checkedDocumentIds, setCheckedDocumentIds] = useState<string[]>(
    documentId ? [documentId] : [],
  );
  const [localSearchScope, setLocalSearchScope] = useState<SearchScope>("current");

  const searchScope = useWorkspaceScope ? SCOPE_TO_UI[workspaceScope] : localSearchScope;
  const setSearchScope = (next: SearchScope) => {
    if (useWorkspaceScope) {
      setWorkspaceScope(UI_TO_SCOPE[next]);
    } else {
      setLocalSearchScope(next);
    }
  };

  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [inlineEditText, setInlineEditText] = useState("");
  const [expandedMessageIds, setExpandedMessageIds] = useState<Set<string>>(new Set());
  const [isAutoScroll, setIsAutoScroll] = useState(true);
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const copiedMessageTimeoutRef = useRef<number | null>(null);
  
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const inlineEditTextareaRef = useRef<HTMLTextAreaElement | null>(null);
  const conversationRef = useRef<HTMLDivElement | null>(null);
  const lastConversationScrollTopRef = useRef(0);
  const abortControllerRef = useRef<AbortController | null>(null);
  const submitInFlightRef = useRef(false);

  const activeDocumentIds = useMemo(() => {
    if (useWorkspaceScope) {
      if (workspaceScope === "ALL_DOCUMENTS") {
        return documents.map((doc) => doc.document_id);
      }
      return workspaceSelectedIds;
    }
    if (searchScope === "all") {
      return documents.map((doc) => doc.document_id);
    }
    if (searchScope === "selected") {
      return checkedDocumentIds;
    }
    return selectedDocumentId ? [selectedDocumentId] : [];
  }, [
    checkedDocumentIds,
    documents,
    searchScope,
    selectedDocumentId,
    useWorkspaceScope,
    workspaceScope,
    workspaceSelectedIds,
  ]);

  const unavailableSelectedDocuments = useMemo(
    () => documents.filter((document) =>
      activeDocumentIds.includes(document.document_id)
      && normalizeDocumentStatus(document.status) !== "indexed",
    ),
    [activeDocumentIds, documents],
  );
  const hasUnavailableSelectedDocuments = unavailableSelectedDocuments.length > 0;
  const unavailableDocumentsMessage = unavailableSelectedDocuments.some(
    (document) => normalizeDocumentStatus(document.status) === "failed",
  )
    ? "A selected document failed to index. Remove it before sending."
    : "A selected document is still being processed. It will be available once indexing finishes.";


  // Auto-resize composer
  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    const nextHeight = Math.min(textarea.scrollHeight, COMPOSER_MAX_HEIGHT);
    textarea.style.height = `${nextHeight}px`;
    textarea.style.overflowY = textarea.scrollHeight > COMPOSER_MAX_HEIGHT ? "auto" : "hidden";
  }, [query]);

  const handleScroll = () => {
    const container = conversationRef.current;
    if (!container) return;
    const { scrollTop, scrollHeight, clientHeight } = container;
    const scrollingUp = scrollTop < lastConversationScrollTopRef.current;
    lastConversationScrollTopRef.current = scrollTop;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 24;

    // Token updates may arrive many times per second. As soon as the user
    // scrolls upward, stop pinning the conversation to the newest token;
    // resume only after they intentionally return to the bottom.
    setIsAutoScroll((current) => {
      const next = scrollingUp ? false : isAtBottom;
      return current === next ? current : next;
    });
  };

  // THE FIX: Scroll tracks chatHistory now, not local messages
  useEffect(() => {
    const container = conversationRef.current;
    if (!container || !isAutoScroll) return;
    container.scrollTop = container.scrollHeight;
  }, [chatHistory, isLoading, isAutoScroll]);

  // Auto-resize inline edit
  useEffect(() => {
    const textarea = inlineEditTextareaRef.current;
    if (!textarea || editingMessageId === null) return;
    textarea.style.height = "auto";
    textarea.style.height = `${textarea.scrollHeight}px`;
    textarea.style.overflowY = "hidden";
  }, [editingMessageId, inlineEditText]);

  useEffect(() => {
    return () => {
      if (copiedMessageTimeoutRef.current !== null) {
        window.clearTimeout(copiedMessageTimeoutRef.current);
      }
    };
  }, []);

  const handleEdit = (messageId: string) => {
    const message = chatHistory.find((item) => item.id === messageId && item.role === "user");
    if (!message) return;

    if (abortControllerRef.current && !abortControllerRef.current.signal.aborted) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    setEditingMessageId(messageId);
    setInlineEditText(message.content);
  };

  const cancelInlineEdit = () => {
    setEditingMessageId(null);
    setInlineEditText("");
  };

  const copyMessageText = async (messageId: string, content: string) => {
    await navigator.clipboard.writeText(content);
    if (copiedMessageTimeoutRef.current !== null) {
      window.clearTimeout(copiedMessageTimeoutRef.current);
    }
    setCopiedMessageId(messageId);
    copiedMessageTimeoutRef.current = window.setTimeout(() => {
      setCopiedMessageId(null);
      copiedMessageTimeoutRef.current = null;
    }, 1500);
  };

  const runContextAction = (prompt: string) => {
    setQuery(prompt);
    textareaRef.current?.focus();
  };

  const toggleMessageExpansion = (messageId: string) => {
    setExpandedMessageIds((current) => {
      const next = new Set(current);
      if (next.has(messageId)) next.delete(messageId);
      else next.add(messageId);
      return next;
    });
  };

  // THE FIX: submitQuery is now totally stripped down. 
  // It just calls the hook and gets out of the way.
  const submitQuery = async (
    prompt: string = query,
    shouldClearComposer = true,
  ) => {
    if (submitInFlightRef.current || isLoading) return;

    const trimmed = prompt.trim();
    if (!trimmed) return;
    if (activeDocumentIds.length === 0) {
      setError("Select at least one document before sending a question.");
      return;
    }
    if (hasUnavailableSelectedDocuments) {
      setError(unavailableDocumentsMessage);
      return;
    }
    
    submitInFlightRef.current = true;
    if (shouldClearComposer) setQuery("");

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      await askQuestion(
        undefined,
        activeDocumentIds,
        trimmed,
        controller.signal,
      );
    } catch (submissionError) {
      console.error(submissionError);
    } finally {
      submitInFlightRef.current = false;
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null;
      }
    }
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await submitQuery();
  };

  const saveInlineEdit = async (messageId: string) => {
    const trimmed = inlineEditText.trim();
    if (!trimmed) return;
    cancelInlineEdit();
    await handleEditMessage(
      messageId,
      trimmed,
      activeDocumentIds,
    );
  };

  return (
    <section className={`flex h-full min-h-0 flex-col overflow-hidden ${chatFocus ? "bg-chat-focus" : "rounded-2xl border border-outline-variant/20 bg-chat-surface shadow-[0_12px_40px_rgba(15,23,42,0.08)]"} ${className ?? ""}`}>
      <div className={`flex flex-col gap-3 ${chatFocus ? "bg-chat-focus px-4 py-4" : "border-b border-outline-variant/20 bg-surface-elevated/80 px-4 py-3 backdrop-blur"}`}>
        <div className="flex items-center justify-between gap-4">
          <div className="flex min-w-0 items-center gap-2">
            {chatFocus && !isChatSidebarOpen && onOpenChatSidebar ? (
              <button
                type="button"
                onClick={onOpenChatSidebar}
                aria-label="Show chat history"
                title="Show chat history"
                className="flex shrink-0 items-center justify-center rounded-lg bg-transparent p-2 text-on-surface-variant transition-colors hover:bg-surface-container hover:text-on-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
              >
                <span className="material-symbols-outlined text-[18px]" aria-hidden="true">
                  dock_to_right
                </span>
              </button>
            ) : null}
            {!chatFocus && <h2 className="text-sm font-semibold text-on-surface">RAG Chat</h2>}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {onToggleExpanded ? (
              <button
                type="button"
                onClick={onToggleExpanded}
                className="rounded-full border border-outline-variant/30 bg-surface-elevated px-3 py-1.5 text-xs text-on-surface-variant shadow-sm transition-colors hover:bg-surface-container focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
              >
                {isExpanded ? "Collapse ⤡" : "Expand ⤢"}
              </button>
            ) : null}
            <button
              type="button"
              onClick={() => {
                setExpandedMessageIds(new Set());
                cancelInlineEdit();
                clearChat();
              }}
              disabled={isLoading}
              className="rounded-full border border-outline-variant/30 bg-surface-elevated px-3 py-1.5 text-xs text-on-surface-variant shadow-sm transition-colors hover:bg-surface-container disabled:opacity-50"
            >
              Clear
            </button>
          </div>
        </div>

        {!isExpanded && (
          <>
            {showDocumentSelector && (
                <div className={`flex w-full flex-col gap-2 rounded-2xl px-1 py-1 ${chatFocus ? "" : "border border-outline-variant/20 bg-surface-container-low/60 sm:px-3 sm:py-2"}`}>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="shrink-0 text-xs font-medium text-on-surface-variant">Search scope:</span>
                    <button
                      type="button"
                      onClick={() => setSearchScope("current")}
                      className={`rounded-full px-2.5 py-1 text-xs transition-colors ${searchScope === "current" ? "bg-primary text-on-primary" : "bg-surface-elevated text-on-surface-variant hover:bg-surface"}`}
                    >
                      This document
                    </button>
                    <button
                      type="button"
                      onClick={() => setSearchScope("selected")}
                      className={`rounded-full px-2.5 py-1 text-xs transition-colors ${searchScope === "selected" ? "bg-primary text-on-primary" : "bg-surface-elevated text-on-surface-variant hover:bg-surface"}`}
                    >
                      Selected documents
                    </button>
                    <button
                      type="button"
                      onClick={() => setSearchScope("all")}
                      className={`rounded-full px-2.5 py-1 text-xs transition-colors ${searchScope === "all" ? "bg-primary text-on-primary" : "bg-surface-elevated text-on-surface-variant hover:bg-surface"}`}
                    >
                      All documents
                    </button>
                    <button
                      type="button"
                      onClick={() => void fetchDocuments()}
                      aria-label="Refresh documents"
                      className="ml-auto shrink-0 rounded-full border border-outline-variant/30 bg-surface-elevated px-3 py-1.5 text-xs text-on-surface-variant transition-colors hover:bg-surface-container"
                    >
                      Refresh
                    </button>
                  </div>
                  <div className="flex min-w-0 items-center gap-2">
                    <label htmlFor="documentSelect" className="shrink-0 text-xs text-on-surface-variant">
                      Current:
                    </label>
                    <select
                      id="documentSelect"
                      value={(useWorkspaceScope ? workspaceSelectedIds[0] : selectedDocumentId) ?? ""}
                      onChange={(e) => {
                        const nextId = e.target.value || null;
                        if (useWorkspaceScope) {
                          setWorkspaceSelectedIds(nextId ? [nextId] : []);
                        } else {
                          setSelectedDocumentId(nextId);
                          if (nextId) {
                            setCheckedDocumentIds((current) => current.includes(nextId) ? current : [...current, nextId]);
                          }
                        }
                      }}
                      className="min-w-0 flex-1 truncate rounded-full border border-outline-variant/30 bg-surface-elevated px-3 py-1.5 text-xs text-on-surface shadow-sm transition-colors focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                      disabled={docsLoading}
                    >
                      <option value="">Choose a document</option>
                      {documents.map((doc) => {
                        const documentStatus = normalizeDocumentStatus(doc.status);
                        const statusLabel = documentStatus === "processing"
                          ? " (still processing)"
                          : documentStatus === "failed"
                            ? " (indexing failed)"
                            : "";
                        return (
                          <option key={doc.document_id} value={doc.document_id}>
                            {doc.original_filename}{statusLabel}
                          </option>
                        );
                      })}
                    </select>
                  </div>
                  {searchScope === "selected" && (
                    <div className="grid max-h-28 gap-1 overflow-y-auto border-t border-outline-variant/15 pt-2 sm:grid-cols-2">
                      {documents.map((doc) => {
                        const isChecked = useWorkspaceScope
                          ? workspaceSelectedIds.includes(doc.document_id)
                          : checkedDocumentIds.includes(doc.document_id);
                        const documentStatus = normalizeDocumentStatus(doc.status);
                        const isProcessing = documentStatus === "processing";
                        const hasFailed = documentStatus === "failed";
                        return (
                          <label key={doc.document_id} className="flex min-w-0 items-center gap-2 text-xs text-on-surface-variant">
                            <input
                              type="checkbox"
                              checked={isChecked}
                              onChange={() => {
                                if (useWorkspaceScope) {
                                  setWorkspaceSelectedIds(
                                    isChecked
                                      ? workspaceSelectedIds.filter((docId) => docId !== doc.document_id)
                                      : [...workspaceSelectedIds, doc.document_id],
                                  );
                                } else {
                                  setCheckedDocumentIds((current) =>
                                    current.includes(doc.document_id)
                                      ? current.filter((id) => id !== doc.document_id)
                                      : [...current, doc.document_id],
                                  );
                                }
                              }}
                              className="accent-primary"
                            />
                            <span className="min-w-0 truncate">{doc.original_filename}</span>
                            {isProcessing && (
                              <span className="shrink-0 rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">
                                Still processing
                              </span>
                            )}
                            {hasFailed && (
                              <span className="shrink-0 rounded-full bg-error/10 px-1.5 py-0.5 text-[10px] font-medium text-error">
                                Indexing failed
                              </span>
                            )}
                          </label>
                        );
                      })}
                    </div>
                  )}
                  {searchScope === "all" && (
                    <p className="text-xs text-on-surface-variant">
                      Searching all {documents.length} loaded documents.
                    </p>
                  )}
                  {searchScope === "selected" && (useWorkspaceScope ? workspaceSelectedIds.length === 0 : checkedDocumentIds.length === 0) && (
                    <p className="text-xs text-error">Select at least one document.</p>
                  )}
                  {searchScope === "current" && !(useWorkspaceScope ? workspaceSelectedIds[0] : selectedDocumentId) && (
                    <p className="text-xs text-error">Choose a document for this scope.</p>
                  )}
                  {hasUnavailableSelectedDocuments && (
                    <p className="text-xs text-primary">{unavailableDocumentsMessage}</p>
                  )}
              </div>
            )}
            <div className="rounded-2xl border border-outline-variant/20 bg-surface-elevated/70 px-3 py-2 shadow-sm">
              <div className="flex flex-wrap items-center gap-2">
                {/* Action buttons remain unchanged */}
                <button type="button" onClick={() => runContextAction("Help me understand the main ideas of this book.")} className="rounded-full border border-outline-variant/30 bg-surface-elevated px-3 py-1.5 text-xs text-on-surface-variant shadow-sm transition-colors hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40">Ask about this book</button>
                <button type="button" onClick={() => runContextAction(`Explain the key ideas on page ${currentPage ?? 1}.`)} className="rounded-full border border-outline-variant/30 bg-surface-elevated px-3 py-1.5 text-xs text-on-surface-variant shadow-sm transition-colors hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40">Explain this page</button>
                <button type="button" disabled={!selectedText?.trim()} onClick={() => runContextAction(`Explain this selection:\n\n${selectedText}`)} className="rounded-full border border-outline-variant/30 bg-surface-elevated px-3 py-1.5 text-xs text-on-surface-variant shadow-sm transition-colors hover:bg-surface disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40" title={selectedText?.trim() ? "Use selected text as context" : "Select text in the document first"}>Explain selection</button>
                <button type="button" onClick={() => runContextAction("Summarize this section in a concise way.")} className="rounded-full border border-outline-variant/30 bg-surface-elevated px-3 py-1.5 text-xs text-on-surface-variant shadow-sm transition-colors hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40">Summarize this section</button>
                <button type="button" onClick={() => runContextAction("Compare this section with another section and explain the key differences.")} className="rounded-full border border-outline-variant/30 bg-surface-elevated px-3 py-1.5 text-xs text-on-surface-variant shadow-sm transition-colors hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40">Compare with another section</button>
              </div>
            </div>
          </>
        )}
      </div>

      <div ref={conversationRef} onScroll={handleScroll} className={`flex-1 overflow-y-auto ${chatFocus ? "bg-chat-focus px-4 py-8 sm:px-8" : "bg-chat-surface p-4"}`}>
        <div className={`mx-auto space-y-7 ${chatFocus ? "w-full max-w-3xl" : ""}`}>
          {chatHistory.length === 0 && !isLoading && (
            <div className="flex h-full min-h-40 items-center justify-center text-center text-sm text-on-surface-variant">
              Ask about this book to get grounded answers with citations.
            </div>
          )}

          {/* THE FIX: Map directly over chatHistory */}
          {chatHistory.map((message) => {
            const isAiMessage = message.role === "assistant";
            const isPendingAssistant = isAiMessage
              && !message.content
              && ["queued", "processing"].includes(message.status || "");
            const canCollapse = isAiMessage && (message.content?.length || 0) > COLLAPSE_THRESHOLD;
            const isExpandedMessage = expandedMessageIds.has(message.id);
            const messageContainerClass = editingMessageId === message.id
              ? "relative w-full max-w-[95%]"
              : message.role === "user"
                ? chatFocus
                  ? "relative w-fit max-w-[88%] rounded-3xl bg-surface-container px-5 py-3 text-on-surface"
                  : "relative w-fit max-w-[88%] rounded-2xl rounded-br-md border border-outline-variant/20 bg-chat-input px-4 py-3 text-on-surface shadow-sm"
                // Assistant answers are rendered directly on the chat surface
                // in both layouts. The boxed treatment is reserved for the
                // user's own messages.
                : "relative w-fit max-w-[92%] text-on-surface";
            
            return (
              <div key={message.id} className={message.role === "user" ? "group flex justify-end" : "group flex justify-start"}>
                <div className={messageContainerClass}>
                  <div className="flex flex-col gap-1">
                    <div className="min-w-0 break-words">
                      {isPendingAssistant ? (
                        <div role="status" className="flex items-center gap-2 py-1 text-sm text-primary">
                          <div className="h-4 w-4 animate-spin rounded-full border-b-2 border-primary" />
                          {statusMessage || "Searching your documents..."}
                        </div>
                      ) : isAiMessage ? (
                        <div className={`relative ${canCollapse && !isExpandedMessage ? "max-h-72 overflow-hidden" : ""}`}>
                          <div className="overflow-x-auto">
                            <div className="prose prose-sm max-w-none text-on-surface prose-p:leading-6 prose-p:mb-3 prose-headings:mb-2 prose-headings:mt-4 prose-headings:text-on-surface prose-p:text-on-surface prose-strong:text-on-surface prose-b:text-on-surface prose-em:text-on-surface prose-ul:text-on-surface prose-ol:text-on-surface prose-li:text-on-surface prose-li:marker:text-on-surface-variant prose-a:text-primary prose-code:text-primary prose-code:bg-surface-container-low prose-pre:bg-surface-container-low prose-pre:text-on-surface prose-blockquote:border-primary prose-blockquote:text-on-surface-variant prose-table:border-outline-variant prose-th:border-outline-variant prose-th:text-on-surface prose-td:border-outline-variant prose-td:text-on-surface-variant prose-hr:border-outline-variant">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                            </div>
                          </div>
                          {canCollapse && !isExpandedMessage && (
                            <div aria-hidden="true" className="pointer-events-none absolute inset-x-0 bottom-0 h-12 bg-linear-to-t from-chat-focus to-transparent" />
                          )}
                        </div>
                      ) : editingMessageId === message.id ? (
                        <div className="w-full min-w-[300px]">
                          <textarea
                            ref={inlineEditTextareaRef}
                            value={inlineEditText}
                            onChange={(e) => {
                              setInlineEditText(e.target.value);
                              if (inlineEditTextareaRef.current) {
                                inlineEditTextareaRef.current.style.height = "auto";
                                inlineEditTextareaRef.current.style.height = `${inlineEditTextareaRef.current.scrollHeight}px`;
                              }
                            }}
                            rows={1}
                            className="w-full resize-none rounded-[24px] border border-primary/40 bg-chat-input p-4 text-sm leading-6 text-on-surface shadow-none transition-colors focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                          />
                          <div className="mt-2 flex items-center justify-end gap-4">
                            <button type="button" onClick={cancelInlineEdit} className="text-sm font-medium text-on-surface-variant transition-colors hover:text-on-surface focus-visible:outline-none">Cancel</button>
                            <button type="button" onClick={() => void saveInlineEdit(message.id)} className="rounded-full bg-primary px-5 py-2 text-sm font-medium text-on-primary shadow-sm transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40">Update</button>
                          </div>
                        </div>
                      ) : (
                        <p className="text-sm">{message.content}</p>
                      )}
                    </div>

                    {canCollapse && (
                      <button type="button" onClick={() => toggleMessageExpansion(message.id)} className="mt-1 self-start text-xs font-medium text-primary transition-colors hover:text-primary/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40">
                        {isExpandedMessage ? "Show less" : "Show more"}
                      </button>
                    )}

                    {message.role === "assistant" && message.citations && message.citations.length > 0 && (
                      <details className="mt-4 text-xs text-on-surface-variant">
                        <summary className="flex cursor-pointer list-none items-center gap-2 text-xs font-medium text-on-surface-variant hover:text-primary">
                          <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-primary/10 px-1.5 text-[11px] text-primary">
                            {message.citations.length}
                          </span>
                          Sources
                          <span className="material-symbols-outlined text-[15px]">expand_more</span>
                        </summary>
                        <div className="mt-2 space-y-2 pl-1">
                          {message.citations.map((citation, index) => (
                            <details key={`${message.id}-${index}`} className="rounded-lg bg-surface-container-low px-2.5 py-2">
                              <summary className="flex cursor-pointer list-none items-center justify-between gap-2 text-on-surface-variant">
                                <span>
                                  <span className="mr-2 text-primary">[{index + 1}]</span>
                                  Source · chunk {citation.chunk_index}
                                </span>
                                {citation.page_number != null && (
                                  <button
                                    type="button"
                                    onClick={(event) => {
                                      event.preventDefault();
                                      onNavigateToPage?.(citation.page_number as number, citation.text);
                                    }}
                                    className="shrink-0 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary transition-colors hover:bg-primary/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
                                  >
                                    Page {citation.page_number}
                                  </button>
                                )}
                              </summary>
                              <p className="mt-2 leading-5 text-on-surface-variant/80">“{citation.text}”</p>
                              <p className="mt-1 text-[10px] text-on-surface-variant/60">Relevance {citation.score.toFixed(3)}</p>
                            </details>
                          ))}
                        </div>
                      </details>
                    )}

                    {editingMessageId !== message.id && !isPendingAssistant && (
                      <div className="mt-1 flex items-end justify-between gap-4 opacity-0 transition-opacity group-hover:opacity-100">
                        <span className="text-[10px] text-on-surface-variant/60">{formatMessageTime(message.created_at)}</span>
                        <div className="flex items-center gap-3">
                          <button
                            type="button"
                            onClick={() => void copyMessageText(message.id, message.content)}
                            className="text-on-surface-variant/60 transition-colors hover:text-on-surface focus-visible:outline-none"
                          >
                            {copiedMessageId === message.id ? (
                              <span className="flex items-center gap-1 text-[10px] font-medium text-success">
                                <span className="material-symbols-outlined text-[16px]">check</span>
                                Copied
                              </span>
                            ) : (
                              <span className="material-symbols-outlined text-[16px]">content_copy</span>
                            )}
                          </button>
                          {message.role === "user" && (
                            <button type="button" onClick={() => handleEdit(message.id)} className="text-on-surface-variant/60 transition-colors hover:text-on-surface focus-visible:outline-none"><span className="material-symbols-outlined text-[16px]">edit</span></button>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}

          {/* Before the assistant placeholder exists, retain a visible status. */}
          {isLoading && !chatHistory.some((message) =>
            message.role === "assistant"
            && !message.content
            && ["queued", "processing"].includes(message.status || ""),
          ) && (
            <div className="flex items-center gap-2 px-1 text-sm text-primary">
              <div className="h-4 w-4 animate-spin rounded-full border-b-2 border-primary" />
              {statusMessage || "Searching vectors and drafting answer..."}
            </div>
          )}

          {error && (
            <div className="rounded-md border border-error/30 bg-error/10 p-3 text-sm text-error">{error}</div>
          )}
        </div>
      </div>

      <div className={`${chatFocus ? "bg-chat-focus px-4 pb-5 pt-3 sm:px-8" : "border-t border-outline-variant/20 bg-surface-elevated/85 p-4 backdrop-blur"}`}>
        <form onSubmit={(e) => void handleSubmit(e)} className={`mx-auto space-y-2 ${chatFocus ? "w-full max-w-3xl" : ""}`}>
          <label htmlFor="rag-chat-composer" className="sr-only">Ask a question about this book</label>
          <div className={`flex items-end gap-3 rounded-3xl p-2 ${chatFocus ? "border border-outline-variant/20 bg-surface-elevated shadow-[0_4px_20px_rgba(0,0,0,0.08)]" : "border border-outline-variant/20 bg-surface-container-low/50 shadow-sm"}`}>
            <div className="relative flex-1">
              <textarea
                id="rag-chat-composer"
                ref={textareaRef}
                rows={1}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.nativeEvent.isComposing) return;
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    if (!isLoading && !hasUnavailableSelectedDocuments && query.trim()) void submitQuery();
                  }
                }}
                placeholder={editingMessageId ? "Edit your message and press Enter to update" : "Ask about this book..."}
                className="max-h-45 w-full resize-none rounded-2xl border border-transparent bg-transparent px-3 py-2 pr-12 text-sm leading-6 text-on-surface shadow-none transition-colors placeholder:text-on-surface-variant/60 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
              <button type="button" disabled className="absolute bottom-2 right-2 inline-flex h-8 w-8 items-center justify-center rounded-full border border-outline-variant/30 bg-surface-elevated/90 text-on-surface-variant opacity-60 shadow-sm"><span className="material-symbols-outlined text-[18px]">mic</span></button>
            </div>
            <button
              type="button"
              onClick={() => {
                if (isLoading) abortControllerRef.current?.abort();
                else void submitQuery();
              }}
              disabled={!isLoading && (!query.trim() || hasUnavailableSelectedDocuments)}
              title={hasUnavailableSelectedDocuments ? unavailableDocumentsMessage : undefined}
              className={`inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border text-on-primary shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 ${
                isLoading ? "border-error bg-error hover:bg-error/90" : query.trim() && !hasUnavailableSelectedDocuments ? "border-primary bg-primary hover:bg-primary/90" : "cursor-not-allowed border-outline bg-outline text-on-surface-variant"
              }`}
            >
              <span className="material-symbols-outlined text-[20px]">{isLoading ? "stop" : "arrow_upward"}</span>
            </button>
          </div>
          <p className="text-xs text-on-surface-variant">Press Enter to send. Press Shift+Enter for a new line.</p>
        </form>
      </div>
    </section>
  );
}
