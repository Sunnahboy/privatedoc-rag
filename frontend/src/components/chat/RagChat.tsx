"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

import { useDocuments } from "@/hooks/useDocuments";
import { useRAGQuery } from "@/hooks/useRAGQuery";

interface RagChatProps {
  documentId?: string;
  currentPage?: number;
  selectedText?: string | null;
  showDocumentSelector?: boolean;
  isExpanded?: boolean;
  chatFocus?: boolean;
  onToggleExpanded?: () => void;
  className?: string;
}

const COMPOSER_MAX_HEIGHT = 180;
const COLLAPSE_THRESHOLD = 950;
type SearchScope = "current" | "selected" | "all";

function formatMessageTime(createdAt?: string) {
  if (!createdAt) {
    return "";
  }
  return new Date(createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function RagChat({
  documentId,
  currentPage,
  selectedText,
  showDocumentSelector = true,
  isExpanded = false,
  chatFocus = false,
  onToggleExpanded,
  className,
}: RagChatProps) {
  // THE FIX: We pull statusMessage directly from the hook now
  const { query, setQuery, isLoading, askQuestion, error, setError, clearChat, chatHistory, handleEditMessage, statusMessage } = useRAGQuery();
  const { documents, isLoading: docsLoading, fetchDocuments } = useDocuments({ autoFetch: showDocumentSelector });

  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(documentId ?? null);
  const [checkedDocumentIds, setCheckedDocumentIds] = useState<string[]>(
    documentId ? [documentId] : [],
  );
  const [searchScope, setSearchScope] = useState<SearchScope>("current");
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [inlineEditText, setInlineEditText] = useState("");
  const [expandedMessageIds, setExpandedMessageIds] = useState<Set<string>>(new Set());
  const [isAutoScroll, setIsAutoScroll] = useState(true);
  
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const inlineEditTextareaRef = useRef<HTMLTextAreaElement | null>(null);
  const conversationRef = useRef<HTMLDivElement | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const submitInFlightRef = useRef(false);

  const activeDocumentIds = useMemo(() => {
    if (searchScope === "all") {
      return documents.map((doc) => doc.document_id);
    }
    if (searchScope === "selected") {
      return checkedDocumentIds;
    }
    return selectedDocumentId ? [selectedDocumentId] : [];
  }, [checkedDocumentIds, documents, searchScope, selectedDocumentId]);

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
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
    setIsAutoScroll(isNearBottom);
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

  const copyMessageText = async (content: string) => {
    await navigator.clipboard.writeText(content);
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
    
    submitInFlightRef.current = true;
    if (shouldClearComposer) setQuery("");

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      if (activeDocumentIds.length === 0) {
        setError("Select at least one document before sending a question.");
        return;
      }
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
        <div className="flex items-center justify-between">
          {!chatFocus && <h2 className="text-sm font-semibold text-on-surface">RAG Chat</h2>}
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
                      value={selectedDocumentId ?? ""}
                      onChange={(e) => {
                        const nextId = e.target.value || null;
                        setSelectedDocumentId(nextId);
                        if (nextId) {
                          setCheckedDocumentIds((current) => current.includes(nextId) ? current : [...current, nextId]);
                        }
                      }}
                      className="min-w-0 flex-1 truncate rounded-full border border-outline-variant/30 bg-surface-elevated px-3 py-1.5 text-xs text-on-surface shadow-sm transition-colors focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                      disabled={docsLoading}
                    >
                      <option value="">Choose a document</option>
                      {documents.map((doc) => (
                        <option key={doc.document_id} value={doc.document_id}>
                          {doc.original_filename}
                        </option>
                      ))}
                    </select>
                  </div>
                  {searchScope === "selected" && (
                    <div className="grid max-h-28 gap-1 overflow-y-auto border-t border-outline-variant/15 pt-2 sm:grid-cols-2">
                      {documents.map((doc) => (
                        <label key={doc.document_id} className="flex min-w-0 items-center gap-2 text-xs text-on-surface-variant">
                          <input
                            type="checkbox"
                            checked={checkedDocumentIds.includes(doc.document_id)}
                            onChange={() => setCheckedDocumentIds((current) =>
                              current.includes(doc.document_id)
                                ? current.filter((id) => id !== doc.document_id)
                                : [...current, doc.document_id],
                            )}
                            className="accent-primary"
                          />
                          <span className="truncate">{doc.original_filename}</span>
                        </label>
                      ))}
                    </div>
                  )}
                  {searchScope === "all" && (
                    <p className="text-xs text-on-surface-variant">
                      Searching all {documents.length} loaded documents.
                    </p>
                  )}
                  {searchScope === "selected" && checkedDocumentIds.length === 0 && (
                    <p className="text-xs text-error">Select at least one document.</p>
                  )}
                  {searchScope === "current" && !selectedDocumentId && (
                    <p className="text-xs text-error">Choose a document for this scope.</p>
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
            const canCollapse = isAiMessage && (message.content?.length || 0) > COLLAPSE_THRESHOLD;
            const isExpandedMessage = expandedMessageIds.has(message.id);
            
            // THE FIX: Hide the empty bubble if it's currently processing!
            // It will only show the text once it actually has text.
            if (isAiMessage && !message.content && ["queued", "processing"].includes(message.status || "")) {
                return null; 
            }

            return (
              <div key={message.id} className={message.role === "user" ? "group flex justify-end" : "group flex justify-start"}>
                <div className={editingMessageId === message.id ? "relative w-full max-w-[95%]" : chatFocus ? message.role === "user" ? "relative w-fit max-w-[88%] rounded-3xl bg-surface-container px-5 py-3 text-on-surface" : "relative w-fit max-w-[92%] text-on-surface" : message.role === "user" ? "relative w-fit max-w-[88%] rounded-2xl rounded-br-md border border-outline-variant/20 bg-chat-input px-4 py-3 text-on-surface shadow-sm" : "relative w-fit max-w-[92%] rounded-2xl rounded-bl-md border border-outline-variant/20 bg-chat-input px-4 py-3 text-on-surface shadow-sm"}>
                  <div className="flex flex-col gap-1">
                    <div className="min-w-0 break-words">
                      {isAiMessage ? (
                        <div className={`relative ${canCollapse && !isExpandedMessage ? "max-h-72 overflow-hidden" : ""}`}>
                          <div className="prose prose-sm max-w-none text-on-surface prose-p:leading-6 prose-p:mb-3 prose-headings:mb-2 prose-headings:mt-4 prose-headings:text-on-surface prose-p:text-on-surface prose-strong:text-on-surface prose-b:text-on-surface prose-em:text-on-surface prose-ul:text-on-surface prose-ol:text-on-surface prose-li:text-on-surface prose-li:marker:text-on-surface-variant prose-a:text-primary prose-code:text-primary prose-code:bg-surface-container-low prose-pre:bg-surface-container-low prose-pre:text-on-surface prose-blockquote:border-primary prose-blockquote:text-on-surface-variant prose-table:border-outline-variant prose-th:border-outline-variant prose-th:text-on-surface prose-td:border-outline-variant prose-td:text-on-surface-variant prose-hr:border-outline-variant">
                            <ReactMarkdown>{message.content}</ReactMarkdown>
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
                              <summary className="cursor-pointer list-none text-on-surface-variant">
                                <span className="mr-2 text-primary">[{index + 1}]</span>
                                Source · chunk {citation.chunk_index}
                              </summary>
                              <p className="mt-2 leading-5 text-on-surface-variant/80">“{citation.text}”</p>
                              <p className="mt-1 text-[10px] text-on-surface-variant/60">Relevance {citation.score.toFixed(3)}</p>
                            </details>
                          ))}
                        </div>
                      </details>
                    )}

                    {editingMessageId !== message.id && (
                      <div className="mt-1 flex items-end justify-between gap-4 opacity-0 transition-opacity group-hover:opacity-100">
                        <span className="text-[10px] text-on-surface-variant/60">{formatMessageTime(message.created_at)}</span>
                        <div className="flex items-center gap-3">
                          <button type="button" onClick={() => void copyMessageText(message.content)} className="text-on-surface-variant/60 transition-colors hover:text-on-surface focus-visible:outline-none"><span className="material-symbols-outlined text-[16px]">content_copy</span></button>
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

          {/* THE FIX: Use the actual backend status message so you know exactly what is happening */}
          {isLoading && (
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
                    if (!isLoading && query.trim()) void submitQuery();
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
              disabled={!isLoading && !query.trim()}
              className={`inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border text-on-primary shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 ${
                isLoading ? "border-error bg-error hover:bg-error/90" : query.trim() ? "border-primary bg-primary hover:bg-primary/90" : "cursor-not-allowed border-outline bg-outline text-on-surface-variant"
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