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

export function RagChat({
  documentId,
  currentPage,
  selectedText,
  showDocumentSelector = true,
  isExpanded = false,
  onToggleExpanded,
  className,
}: RagChatProps) {
  const { query, setQuery, isLoading, askQuestion, error, clearChat } = useRAGQuery();
  const { documents, isLoading: docsLoading, fetchDocuments } = useDocuments({ autoFetch: showDocumentSelector });

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(documentId ?? null);
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [expandedMessageIds, setExpandedMessageIds] = useState<Set<string>>(new Set());
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const conversationRef = useRef<HTMLDivElement | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

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
    setQuery(message.content);
    textareaRef.current?.focus();
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

  const submitQuery = async () => {
    const trimmed = query.trim();
    if (!trimmed) {
      return;
    }

    let nextMessages: ChatMessage[] = [];
    if (editingMessageId) {
      const index = messages.findIndex((message) => message.id === editingMessageId);
      nextMessages = index === -1 ? [...messages] : messages.slice(0, index);
      nextMessages = [...nextMessages, { id: editingMessageId, role: "user", content: trimmed }];
    } else {
      nextMessages = [...messages, { id: makeId(), role: "user", content: trimmed }];
    }

    setMessages(nextMessages);
    setQuery("");
    setEditingMessageId(null);

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
            citations: result.citations,
          },
        ]);
        return;
      }

      if (!controller.signal.aborted) {
        setMessages([...nextMessages, { id: makeId(), role: "ai", content: "Failed to get an answer. Please try again." }]);
      }
    } catch (submissionError) {
      if (!isAbortError(submissionError)) {
        setMessages([...nextMessages, { id: makeId(), role: "ai", content: "Failed to get an answer. Please try again." }]);
      }
    } finally {
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null;
      }
    }
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await submitQuery();
  };

  return (
    <section className={`flex h-full min-h-0 flex-col border border-outline-variant/20 bg-white ${className ?? ""}`}>
      <div className="flex items-center justify-between gap-3 border-b border-outline-variant/20 bg-surface px-4 py-3">
        <div className="flex min-w-0 items-center gap-3">
          <h2 className="truncate text-sm font-semibold text-on-surface">RAG Chat</h2>

          {showDocumentSelector && (
            <div className="flex items-center gap-2">
              <label htmlFor="documentSelect" className="text-xs text-on-surface-variant">
                Scope:
              </label>
              <select
                id="documentSelect"
                value={selectedDocumentId ?? ""}
                onChange={(changeEvent) => setSelectedDocumentId(changeEvent.target.value || null)}
                className="rounded-md border border-outline-variant/30 px-2 py-1 text-xs"
                disabled={docsLoading}
              >
                <option value="">All documents</option>
                {documents.map((doc) => (
                  <option key={doc.document_id} value={doc.document_id}>
                    {doc.original_filename}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => void fetchDocuments()}
                className="rounded-md border border-outline-variant/30 px-2 py-1 text-xs text-on-surface-variant transition-colors hover:bg-surface-container"
              >
                Refresh
              </button>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          {onToggleExpanded ? (
            <button
              type="button"
              aria-label={isExpanded ? "Collapse RAG Chat panel" : "Expand RAG Chat panel"}
              aria-expanded={isExpanded}
              onClick={onToggleExpanded}
              className="rounded-md border border-outline-variant/30 px-2 py-1 text-xs text-on-surface-variant transition-colors hover:bg-surface-container focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
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
              clearChat();
              setQuery("");
            }}
            disabled={isLoading}
            className="rounded-md border border-outline-variant/30 px-2 py-1 text-xs text-on-surface-variant transition-colors hover:bg-surface-container disabled:opacity-50"
          >
            Clear
          </button>
        </div>
      </div>

      <div className="border-b border-outline-variant/20 bg-white px-4 py-2">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => runContextAction("Help me understand the main ideas of this book.")}
            className="rounded-md border border-outline-variant/30 px-2 py-1 text-xs text-on-surface-variant transition-colors hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
          >
            Ask about this book
          </button>
          <button
            type="button"
            onClick={() => runContextAction(`Explain the key ideas on page ${currentPage ?? 1}.`)}
            className="rounded-md border border-outline-variant/30 px-2 py-1 text-xs text-on-surface-variant transition-colors hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
          >
            Explain this page
          </button>
          <button
            type="button"
            disabled={!selectedText?.trim()}
            onClick={() => runContextAction(`Explain this selection:\n\n${selectedText}`)}
            className="rounded-md border border-outline-variant/30 px-2 py-1 text-xs text-on-surface-variant transition-colors hover:bg-surface disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
            title={selectedText?.trim() ? "Use selected text as context" : "Select text in the document first"}
          >
            Explain selection
          </button>
          <button
            type="button"
            onClick={() => runContextAction("Summarize this section in a concise way.")}
            className="rounded-md border border-outline-variant/30 px-2 py-1 text-xs text-on-surface-variant transition-colors hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
          >
            Summarize this section
          </button>
          <button
            type="button"
            onClick={() => runContextAction("Compare this section with another section and explain the key differences.")}
            className="rounded-md border border-outline-variant/30 px-2 py-1 text-xs text-on-surface-variant transition-colors hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
          >
            Compare with another section
          </button>
        </div>
      </div>

      <div ref={conversationRef} className="flex-1 overflow-y-auto bg-[#faf9f6] p-4">
        <div className="space-y-4">
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
              <div key={message.id} className={message.role === "user" ? "flex justify-end" : "flex justify-start"}>
                <div
                  className={
                    message.role === "user"
                      ? "max-w-[88%] rounded-md bg-primary px-4 py-2 text-on-primary"
                      : "max-w-[92%] rounded-md border border-outline-variant/20 bg-white px-4 py-3"
                  }
                >
                  <div className="flex items-start gap-2">
                    <div className="min-w-0 flex-1">
                      {isAiMessage ? (
                        <div className={`relative ${canCollapse && !isExpandedMessage ? "max-h-72 overflow-hidden" : ""}`}>
                          <div className="prose prose-sm max-w-none text-on-surface">
                            <ReactMarkdown>{message.content}</ReactMarkdown>
                          </div>
                          {canCollapse && !isExpandedMessage ? (
                            <div
                              aria-hidden="true"
                              className="pointer-events-none absolute inset-x-0 bottom-0 h-12 bg-linear-to-t from-white to-transparent"
                            />
                          ) : null}
                        </div>
                      ) : (
                        <p className="text-sm">{message.content}</p>
                      )}
                    </div>

                    {message.role === "user" && (
                      <button
                        type="button"
                        onClick={() => handleEdit(message.id)}
                        className="rounded border border-outline-variant/30 bg-white px-2 py-1 text-xs text-on-surface-variant transition-colors hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
                      >
                        Edit
                      </button>
                    )}
                  </div>

                  {canCollapse ? (
                    <button
                      type="button"
                      onClick={() => toggleMessageExpansion(message.id)}
                      className="mt-2 text-xs font-medium text-primary transition-colors hover:text-primary/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                    >
                      {isExpandedMessage ? "Show less" : "Show more"}
                    </button>
                  ) : null}

                  {message.role === "ai" && message.citations && message.citations.length > 0 && (
                    <div className="mt-3 space-y-2 text-xs text-on-surface-variant">
                      <p className="font-medium text-on-surface">Sources</p>
                      {message.citations.map((citation, index) => (
                        <div key={`${message.id}-${index}`} className="rounded border border-outline-variant/20 bg-surface-container-low p-2">
                          <div className="flex items-center justify-between gap-2">
                            <span>Chunk {citation.chunk_index}</span>
                            <span>Score {citation.score.toFixed(3)}</span>
                          </div>
                          <p className="mt-1 line-clamp-2 text-xs">“{citation.text}”</p>
                        </div>
                      ))}
                    </div>
                  )}
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

      <div className="border-t border-outline-variant/20 bg-white p-4">
        <form onSubmit={(event) => void handleSubmit(event)} className="space-y-2">
          <label htmlFor="rag-chat-composer" className="sr-only">
            Ask a question about this book
          </label>
          <div className="flex items-end gap-2">
            <div className="relative flex-1">
              <textarea
                id="rag-chat-composer"
                ref={textareaRef}
                rows={1}
                value={query}
                onChange={(changeEvent) => setQuery(changeEvent.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    if (!isLoading && query.trim()) {
                      void submitQuery();
                    }
                  }
                }}
                placeholder={editingMessageId ? "Edit your message and press Enter to update" : "Ask about this book..."}
                aria-label="RAG Chat question input"
                className="max-h-45 w-full resize-none rounded-md border border-outline-variant/30 bg-surface-container-low px-3 py-2 pr-12 text-sm leading-6 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
              <button
                type="button"
                disabled
                aria-label="Voice input coming soon"
                title="Voice input coming soon"
                className="absolute bottom-2 right-2 inline-flex h-8 w-8 items-center justify-center rounded-md border border-outline-variant/30 text-on-surface-variant opacity-60"
              >
                <span className="material-symbols-outlined text-[18px]">mic</span>
              </button>
            </div>

            {isLoading && (
              <button
                type="button"
                onClick={() => abortControllerRef.current?.abort()}
                className="h-10 rounded-md bg-red-600 px-3 text-sm font-medium text-white transition-colors hover:bg-red-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
              >
                Stop
              </button>
            )}

            <button
              type="submit"
              disabled={isLoading || !query.trim()}
              className="h-10 rounded-md bg-primary px-4 text-sm font-medium text-on-primary transition-colors hover:bg-primary/90 disabled:bg-outline disabled:text-on-surface-variant focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
            >
              {editingMessageId ? "Update" : "Ask"}
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
