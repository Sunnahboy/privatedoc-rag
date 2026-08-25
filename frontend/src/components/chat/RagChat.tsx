"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

import { type Citation } from "@/lib/api-client";
import { useDocuments } from "@/hooks/useDocuments";
import { useRAGQuery } from "@/hooks/useRAGQuery";

type ChatMessage = {
  id: string;
  role: "user" | "ai";
  content: string;
  created_at?: string;
  citations?: Citation[];
};

interface RagChatProps {
  documentId?: string;
  currentPage?: number;
  selectedText?: string | null;
  showDocumentSelector?: boolean;
  isExpanded?: boolean;
  onToggleExpanded?: () => void;
  className?: string;
}

function makeId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

const COMPOSER_MAX_HEIGHT = 180;
const COLLAPSE_THRESHOLD = 950;

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
  onToggleExpanded,
  className,
}: RagChatProps) {
  const { query, setQuery, isLoading, askQuestion, error, clearChat, chatHistory } = useRAGQuery();
  const { documents, isLoading: docsLoading, fetchDocuments } = useDocuments({ autoFetch: showDocumentSelector });

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(documentId ?? null);
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [inlineEditText, setInlineEditText] = useState("");
  const [expandedMessageIds, setExpandedMessageIds] = useState<Set<string>>(new Set());
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const inlineEditTextareaRef = useRef<HTMLTextAreaElement | null>(null);
  const conversationRef = useRef<HTMLDivElement | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const submitInFlightRef = useRef(false);

  // Sync database history into the UI!
  useEffect(() => {
    if (chatHistory && chatHistory.length > 0) {
      setMessages(
        chatHistory.map((msg) => ({
          id: msg.id,
          // Map backend "assistant" to frontend "ai"
          role: msg.role === "assistant" ? "ai" : "user",
          content: msg.content,
          created_at: msg.created_at,
          citations: msg.citations,
        }))
      );
    }
  }, [chatHistory]);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) {
      return;
    }

    textarea.style.height = "auto";
    const nextHeight = Math.min(textarea.scrollHeight, COMPOSER_MAX_HEIGHT);
    textarea.style.height = `${nextHeight}px`;
    textarea.style.overflowY = textarea.scrollHeight > COMPOSER_MAX_HEIGHT ? "auto" : "hidden";
  }, [query]);

  useEffect(() => {
    const container = conversationRef.current;
    if (!container) {
      return;
    }
    container.scrollTop = container.scrollHeight;
  }, [messages, isLoading]);

  useEffect(() => {
    const textarea = inlineEditTextareaRef.current;
    if (!textarea || editingMessageId === null) {
      return;
    }

    textarea.style.height = "auto";
    textarea.style.height = `${textarea.scrollHeight}px`;
    textarea.style.overflowY = "hidden";
  }, [editingMessageId, inlineEditText]);

  const handleEdit = (messageId: string) => {
    const message = messages.find((item) => item.id === messageId && item.role === "user");
    if (!message) {
      return;
    }

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
      if (next.has(messageId)) {
        next.delete(messageId);
      } else {
        next.add(messageId);
      }
      return next;
    });
  };

  const submitQuery = async (
    prompt: string = query,
    baseMessages: ChatMessage[] = messages,
    shouldClearComposer = true,
  ) => {
    if (submitInFlightRef.current || isLoading) {
      return;
    }

    const trimmed = prompt.trim();
    if (!trimmed) {
      return;
    }
    submitInFlightRef.current = true;

    const now = new Date().toISOString();
    const nextMessages: ChatMessage[] = [
      ...baseMessages,
      { id: makeId(), role: "user", content: trimmed, created_at: now },
    ];

    setMessages(nextMessages);
    if (shouldClearComposer) {
      setQuery("");
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const scopedDocument = documentId ?? selectedDocumentId;
      const result = await askQuestion(
        undefined,
        scopedDocument ? [scopedDocument] : undefined,
        trimmed,
        controller.signal,
      );

      if (result) {
        setMessages([
          ...nextMessages,
          {
            id: makeId(),
            role: "ai",
            content: result.answer,
            created_at: new Date().toISOString(),
            citations: result.citations,
          },
        ]);
        return;
      }

      if (!controller.signal.aborted) {
        setMessages([
          ...nextMessages,
          {
            id: makeId(),
            role: "ai",
            content: "Failed to get an answer. Please try again.",
            created_at: new Date().toISOString(),
          },
        ]);
      }
    } catch (submissionError) {
      if (!isAbortError(submissionError)) {
        setMessages([
          ...nextMessages,
          {
            id: makeId(),
            role: "ai",
            content: "Failed to get an answer. Please try again.",
            created_at: new Date().toISOString(),
          },
        ]);
      }
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
    if (!trimmed) {
      return;
    }

    const index = messages.findIndex((message) => message.id === messageId);
    const truncatedMessages = index === -1 ? messages : messages.slice(0, index);

    setMessages(truncatedMessages);
    cancelInlineEdit();
    await submitQuery(trimmed, truncatedMessages, false);
  };

  return (
    <section
      className={`flex h-full min-h-0 flex-col overflow-hidden rounded-2xl border border-outline-variant/20 bg-[#FCFBF8] shadow-[0_12px_40px_rgba(15,23,42,0.08)] ${className ?? ""}`}
    >
      <div className="flex flex-col gap-3 border-b border-outline-variant/20 bg-white/80 px-4 py-3 backdrop-blur">
        {/* Top Row: Title & Action Buttons */}
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-on-surface">RAG Chat</h2>
          <div className="flex items-center gap-2">
            {onToggleExpanded ? (
              <button
                type="button"
                aria-label={isExpanded ? "Collapse RAG Chat panel" : "Expand RAG Chat panel"}
                aria-expanded={isExpanded}
                onClick={onToggleExpanded}
                className="rounded-full border border-outline-variant/30 bg-white px-3 py-1.5 text-xs text-on-surface-variant shadow-sm transition-colors hover:bg-surface-container focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
                title={isExpanded ? "Collapse panel" : "Expand panel"}
              >
                {isExpanded ? "Collapse ⤡" : "Expand ⤢"}
              </button>
            ) : null}
            <button
              type="button"
              onClick={() => {
                setMessages([]);
                setExpandedMessageIds(new Set());
                cancelInlineEdit();
                clearChat();
                setQuery("");
              }}
              disabled={isLoading}
              className="rounded-full border border-outline-variant/30 bg-white px-3 py-1.5 text-xs text-on-surface-variant shadow-sm transition-colors hover:bg-surface-container disabled:opacity-50"
            >
              Clear
            </button>
          </div>
        </div>

        {!isExpanded && (
          <>
            {/* Bottom Row: Scope Selector */}
            {showDocumentSelector && (
              <div className="flex w-full items-center gap-2 rounded-2xl border border-outline-variant/20 bg-surface-container-low/60 px-3 py-2">
                <label htmlFor="documentSelect" className="shrink-0 text-xs font-medium text-on-surface-variant">
                  Scope:
                </label>
                <div className="flex min-w-0 flex-1 items-center gap-2">
                  <select
                    id="documentSelect"
                    value={selectedDocumentId ?? ""}
                    onChange={(changeEvent) => setSelectedDocumentId(changeEvent.target.value || null)}
                    className="w-full min-w-0 truncate rounded-full border border-outline-variant/30 bg-white px-3 py-1.5 text-xs text-on-surface shadow-sm transition-colors focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                    disabled={docsLoading}
                  >
                    <option value="">All documents in Library</option>
                    {documents.map((doc) => (
                      <option key={doc.document_id} value={doc.document_id}>
                        {doc.original_filename}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => void fetchDocuments()}
                    className="shrink-0 rounded-full border border-outline-variant/30 bg-white px-3 py-1.5 text-xs text-on-surface-variant shadow-sm transition-colors hover:bg-surface-container"
                  >
                    Refresh
                  </button>
                </div>
              </div>
            )}

            <div className="rounded-2xl border border-outline-variant/20 bg-white/70 px-3 py-2 shadow-sm">
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => runContextAction("Help me understand the main ideas of this book.")}
                  className="rounded-full border border-outline-variant/30 bg-white px-3 py-1.5 text-xs text-on-surface-variant shadow-sm transition-colors hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                >
                  Ask about this book
                </button>
                <button
                  type="button"
                  onClick={() => runContextAction(`Explain the key ideas on page ${currentPage ?? 1}.`)}
                  className="rounded-full border border-outline-variant/30 bg-white px-3 py-1.5 text-xs text-on-surface-variant shadow-sm transition-colors hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                >
                  Explain this page
                </button>
                <button
                  type="button"
                  disabled={!selectedText?.trim()}
                  onClick={() => runContextAction(`Explain this selection:\n\n${selectedText}`)}
                  className="rounded-full border border-outline-variant/30 bg-white px-3 py-1.5 text-xs text-on-surface-variant shadow-sm transition-colors hover:bg-surface disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                  title={selectedText?.trim() ? "Use selected text as context" : "Select text in the document first"}
                >
                  Explain selection
                </button>
                <button
                  type="button"
                  onClick={() => runContextAction("Summarize this section in a concise way.")}
                  className="rounded-full border border-outline-variant/30 bg-white px-3 py-1.5 text-xs text-on-surface-variant shadow-sm transition-colors hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                >
                  Summarize this section
                </button>
                <button
                  type="button"
                  onClick={() => runContextAction("Compare this section with another section and explain the key differences.")}
                  className="rounded-full border border-outline-variant/30 bg-white px-3 py-1.5 text-xs text-on-surface-variant shadow-sm transition-colors hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                >
                  Compare with another section
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      <div ref={conversationRef} className="flex-1 overflow-y-auto bg-[linear-gradient(180deg,#faf8f2_0%,#f7f5ef_100%)] p-4">
        <div className="space-y-5">
          {messages.length === 0 && !isLoading && (
            <div className="flex h-full min-h-40 items-center justify-center text-center text-sm text-on-surface-variant">
              Ask about this book to get grounded answers with citations.
            </div>
          )}

          {messages.map((message) => {
            const isAiMessage = message.role === "ai";
            const canCollapse = isAiMessage && message.content.length > COLLAPSE_THRESHOLD;
            const isExpandedMessage = expandedMessageIds.has(message.id);

            return (
              <div key={message.id} className={message.role === "user" ? "group flex justify-end" : "group flex justify-start"}>
                <div
                  className={
                    editingMessageId === message.id
                      ? "relative w-full max-w-[95%]"
                      : message.role === "user"
                        ? "relative w-fit max-w-[88%] rounded-2xl rounded-br-md border border-outline-variant/20 bg-[#faf9f6] px-4 py-3 text-on-surface shadow-sm"
                        : "relative w-fit max-w-[92%] rounded-2xl rounded-bl-md border border-outline-variant/20 bg-[#faf9f6] px-4 py-3 text-on-surface shadow-sm"
                  }
                >
                  <div className="flex flex-col gap-1">
                    <div className="min-w-0 break-words">
                      {isAiMessage ? (
                        <div className={`relative ${canCollapse && !isExpandedMessage ? "max-h-72 overflow-hidden" : ""}`}>
                          <div className="prose prose-sm max-w-none text-on-surface prose-p:leading-6 prose-p:mb-3 prose-headings:mb-2 prose-headings:mt-4 prose-a:text-primary">
                            <ReactMarkdown>{message.content}</ReactMarkdown>
                          </div>
                          {canCollapse && !isExpandedMessage ? (
                            <div
                              aria-hidden="true"
                              className="pointer-events-none absolute inset-x-0 bottom-0 h-12 bg-linear-to-t from-white to-transparent"
                            />
                          ) : null}
                        </div>
                      ) : editingMessageId === message.id ? (
                        <div className="w-full min-w-[300px]">
                          <textarea
                            ref={inlineEditTextareaRef}
                            value={inlineEditText}
                            onChange={(changeEvent) => {
                              setInlineEditText(changeEvent.target.value);
                              const textarea = inlineEditTextareaRef.current;
                              if (!textarea) return;
                              textarea.style.height = "auto";
                              textarea.style.height = `${textarea.scrollHeight}px`;
                            }}
                            rows={1}
                            className="w-full resize-none rounded-[24px] border border-primary/40 bg-[#faf9f6] p-4 text-sm leading-6 text-on-surface shadow-none transition-colors focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                            aria-label="Edit message"
                          />
                          <div className="mt-2 flex items-center justify-end gap-4">
                            <button
                              type="button"
                              onClick={cancelInlineEdit}
                              className="text-sm font-medium text-on-surface-variant transition-colors hover:text-on-surface focus-visible:outline-none"
                            >
                              Cancel
                            </button>
                            <button
                              type="button"
                              onClick={() => void saveInlineEdit(message.id)}
                              className="rounded-full bg-primary px-5 py-2 text-sm font-medium text-on-primary shadow-sm transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                            >
                              Update
                            </button>
                          </div>
                        </div>
                      ) : (
                        <p className="text-sm">{message.content}</p>
                      )}
                    </div>

                    {canCollapse ? (
                      <button
                        type="button"
                        onClick={() => toggleMessageExpansion(message.id)}
                        className="mt-1 self-start text-xs font-medium text-primary transition-colors hover:text-primary/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                      >
                        {isExpandedMessage ? "Show less" : "Show more"}
                      </button>
                    ) : null}

                    {message.role === "ai" && message.citations && message.citations.length > 0 && (
                      <div className="mt-3 space-y-2 text-xs text-on-surface-variant">
                        <p className="font-medium text-on-surface">Sources</p>
                        {message.citations.map((citation, index) => (
                          <div key={`${message.id}-${index}`} className="rounded-2xl border border-outline-variant/20 bg-surface-container-low p-2.5">
                            <div className="flex items-center justify-between gap-2">
                              <span>Chunk {citation.chunk_index}</span>
                              <span>Score {citation.score.toFixed(3)}</span>
                            </div>
                            <p className="mt-1 line-clamp-2 text-xs">“{citation.text}”</p>
                          </div>
                        ))}
                      </div>
                    )}

                    {editingMessageId !== message.id && (
                      <div className="mt-1 flex items-end justify-between gap-4 opacity-0 transition-opacity group-hover:opacity-100">
                        <span className="text-[10px] text-on-surface-variant/60">
                          {formatMessageTime(message.created_at)}
                        </span>

                        <div className="flex items-center gap-3">
                          <button
                            type="button"
                            title="Copy"
                            aria-label="Copy message"
                            onClick={() => {
                              void copyMessageText(message.content);
                            }}
                            className={
                              "text-on-surface-variant/60 transition-colors hover:text-on-surface focus-visible:outline-none"
                            }
                          >
                            <span className="material-symbols-outlined text-[16px]">content_copy</span>
                          </button>

                          {message.role === "user" && (
                            <button
                              type="button"
                              title="Edit"
                              aria-label="Edit message"
                              onClick={() => handleEdit(message.id)}
                              className="text-on-surface-variant/60 transition-colors hover:text-on-surface focus-visible:outline-none"
                            >
                              <span className="material-symbols-outlined text-[16px]">edit</span>
                            </button>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}

          {isLoading && (
            <div className="flex items-center gap-2 px-1 text-sm text-primary">
              <div className="h-4 w-4 animate-spin rounded-full border-b-2 border-primary" />
              Searching vectors and drafting answer...
            </div>
          )}

          {error && (
            <div className="rounded-md border border-red-100 bg-red-50 p-3 text-sm text-red-700">{error}</div>
          )}
        </div>
      </div>

      <div className="border-t border-outline-variant/20 bg-white/85 p-4 backdrop-blur">
        <form onSubmit={(event) => void handleSubmit(event)} className="space-y-2">
          <label htmlFor="rag-chat-composer" className="sr-only">
            Ask a question about this book
          </label>
          <div className="flex items-end gap-3 rounded-2xl border border-outline-variant/20 bg-surface-container-low/50 p-2 shadow-sm">
            <div className="relative flex-1">
              <textarea
                id="rag-chat-composer"
                ref={textareaRef}
                rows={1}
                value={query}
                onChange={(changeEvent) => setQuery(changeEvent.target.value)}
                onKeyDown={(event) => {
                  if (event.nativeEvent.isComposing) {
                    return;
                  }

                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    if (!isLoading && query.trim()) {
                      void submitQuery();
                    }
                  }
                }}
                placeholder={editingMessageId ? "Edit your message and press Enter to update" : "Ask about this book..."}
                aria-label="RAG Chat question input"
                className="max-h-45 w-full resize-none rounded-2xl border border-transparent bg-white/90 px-3 py-2 pr-12 text-sm leading-6 text-on-surface shadow-sm transition-colors placeholder:text-on-surface-variant/60 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
              <button
                type="button"
                disabled
                aria-label="Voice input coming soon"
                title="Voice input coming soon"
                className="absolute bottom-2 right-2 inline-flex h-8 w-8 items-center justify-center rounded-full border border-outline-variant/30 bg-white/90 text-on-surface-variant opacity-60 shadow-sm"
              >
                <span className="material-symbols-outlined text-[18px]">mic</span>
              </button>
            </div>

            <button
              type="button"
              onClick={() => {
                if (isLoading) {
                  abortControllerRef.current?.abort();
                  return;
                }

                void submitQuery();
              }}
              disabled={!isLoading && !query.trim()}
              aria-label={
                isLoading
                  ? "Stop generating response"
                  : editingMessageId
                    ? "Update message"
                    : "Send message"
              }
              title={
                isLoading
                  ? "Stop"
                  : editingMessageId
                    ? "Update"
                    : "Send"
              }
              className={`inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border text-on-primary shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 ${
                isLoading
                  ? "border-red-600 bg-red-600 hover:bg-red-700 focus-visible:ring-red-400"
                  : query.trim()
                    ? "border-primary bg-primary hover:bg-primary/90"
                    : "cursor-not-allowed border-outline bg-outline text-on-surface-variant"
              }`}
            >
              <span className="material-symbols-outlined text-[20px]">
                {isLoading ? "stop" : "arrow_upward"}
              </span>
            </button>
          </div>
          <p className="text-xs text-on-surface-variant">
            Press Enter to send. Press Shift+Enter for a new line.
          </p>
        </form>
      </div>
    </section>
  );
}
