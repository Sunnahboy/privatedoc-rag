"use client";

import { useRAGQuery } from "@/hooks/useRAGQuery";
import { useDocuments } from "@/hooks/useDocuments";
import ReactMarkdown from 'react-markdown';
import { useState, useEffect, useRef } from 'react';

type Message = {
  id: string;
  role: 'user' | 'ai';
  content: string;
  citations?: any[];
};

export function RagChat() {
  // RAG hook handles the network call and loading state
  const { query, setQuery, isLoading, askQuestion, error, clearChat } = useRAGQuery();
  // Document list for the dropdown
  const { documents, isLoading: docsLoading, fetchDocuments } = useDocuments();

  const [messages, setMessages] = useState<Message[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);

  const inputRef = useRef<HTMLInputElement | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // helper to generate ids safely in browsers that support crypto.randomUUID
  const makeId = () => {
    try {
      // @ts-ignore
      return typeof crypto !== 'undefined' && typeof (crypto as any).randomUUID === 'function'
        ? (crypto as any).randomUUID()
        : Date.now().toString();
    } catch (err) {
      return Date.now().toString();
    }
  };

  // When a document upload completes elsewhere, the parent can call fetchDocuments().
  // This component also exposes a manual refresh through the dropdown UI.

  // Handle edit click on a user message
  const handleEdit = (msgId: string) => {
    const msg = messages.find((m) => m.id === msgId && m.role === 'user');
    if (!msg) return;

    // If the model is currently generating, abort the request so the UI unlocks immediately
    if (abortControllerRef.current && !abortControllerRef.current.signal.aborted) {
      try {
        abortControllerRef.current.abort();
      } catch (err) {
        console.error('Failed to abort ongoing generation:', err);
      }
      // leave the controller to be cleared by the submit flow's finally block or clear now
      abortControllerRef.current = null;
    }

    setEditingMessageId(msgId);
    setQuery(msg.content);
    inputRef.current?.focus();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;

    // Prepare the staged user message
    let newMessages: Message[] = [];

    if (editingMessageId) {
      // Find index of the edited message, replace its content and truncate history after it
      const idx = messages.findIndex((m) => m.id === editingMessageId);
      if (idx === -1) {
        // fallback: just append
        newMessages = [...messages];
      } else {
        newMessages = messages.slice(0, idx);
      }
      const updatedUserMsg: Message = { id: editingMessageId, role: 'user', content: trimmed };
      newMessages = [...newMessages, updatedUserMsg];
    } else {
      // Normal new message: append to history
      const userMsg: Message = { id: makeId(), role: 'user', content: trimmed };
      newMessages = [...messages, userMsg];
    }

    // Stage to UI and clear input once staged
    setMessages(newMessages);
    setQuery('');
    setEditingMessageId(null);

    // Trigger the backend call. Pass selectedDocumentId if provided.
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const docs = selectedDocumentId ? [selectedDocumentId] : undefined;
      // Pass the trimmed query explicitly to avoid races with the hook's internal query state
      const result = await askQuestion(undefined, docs, trimmed, controller.signal);

      if (result) {
        const aiMsg: Message = { id: makeId(), role: 'ai', content: result.answer, citations: result.citations };
        setMessages((prev) => [...newMessages, aiMsg]);
      } else {
        // If the request was aborted, do not append a failure message
        if (!controller.signal.aborted) {
          const failMsg: Message = { id: makeId(), role: 'ai', content: 'Failed to get an answer. Please try again.' };
          setMessages((prev) => [...newMessages, failMsg]);
        }
      }
    } catch (err) {
      // If the error is an abort, don't append a failure message
      const isAbort = typeof err === 'object' && err !== null && (err as any).name === 'AbortError';
      if (!isAbort) {
        console.error('askQuestion failed', err);
        const failMsg: Message = { id: makeId(), role: 'ai', content: 'Failed to get an answer. Please try again.' };
        setMessages((prev) => [...newMessages, failMsg]);
      }
    } finally {
      // clear controller reference so subsequent edits/submits start fresh
      if (abortControllerRef.current === controller) abortControllerRef.current = null;
    }
  };

  return (
    <div className="w-full bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden flex flex-col h-[600px]">
      {/* Header: title + docs dropdown + clear */}
      <div className="bg-gray-50 border-b border-gray-100 p-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <h2 className="font-semibold text-gray-800">Ask Your Documents</h2>
          <div className="flex items-center gap-2">
            <label htmlFor="documentSelect" className="text-sm text-gray-500">Document:</label>
            <select
              id="documentSelect"
              value={selectedDocumentId ?? ''}
              onChange={(e) => setSelectedDocumentId(e.target.value || null)}
              className="px-3 py-1 bg-white border border-gray-200 rounded-md text-sm"
              disabled={docsLoading}
            >
              <option value="">(All documents)</option>
              {documents.map((d) => (
                <option key={d.document_id} value={d.document_id}>{d.original_filename}</option>
              ))}
            </select>
            <button
              onClick={() => fetchDocuments()}
              className="text-xs px-2 py-1 border border-gray-200 rounded text-gray-600 hover:bg-gray-50"
            >
              Refresh
            </button>
          </div>
        </div>

        <div>
          <button
            onClick={() => { setMessages([]); clearChat(); setQuery(''); }}
            disabled={isLoading}
            className="text-xs font-medium text-gray-500 hover:text-gray-900 bg-white border border-gray-200 hover:bg-gray-100 px-3 py-1 rounded transition-colors disabled:opacity-50"
          >
            Clear Chat
          </button>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-6 bg-gray-50 space-y-4">
        {messages.length === 0 && !isLoading && (
          <div className="h-full flex items-center justify-center text-gray-400">Ask a question to search your indexed documents.</div>
        )}

        {messages.map((m) => (
          <div key={m.id} className={m.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
            <div className={m.role === 'user' ? 'bg-blue-600 text-white px-4 py-2 rounded-lg max-w-[80%]' : 'bg-white border border-gray-100 px-4 py-2 rounded-lg max-w-[80%]'}>
              <div className="flex items-start gap-3">
                <div className="flex-1">
                  {m.role === 'ai' ? (
                    <div className="prose prose-sm max-w-none text-gray-800"><ReactMarkdown>{m.content}</ReactMarkdown></div>
                  ) : (
                    <div className="text-sm">{m.content}</div>
                  )}
                </div>
                {m.role === 'user' && (
                  <div className="ml-2 self-start">
                    <button
                      onClick={() => handleEdit(m.id)}
                      className="text-xs text-gray-500 bg-white border border-gray-200 px-2 py-1 rounded hover:bg-gray-50"
                    >
                      Edit
                    </button>
                  </div>
                )}
              </div>

              {/* If AI message has citations, render brief list */}
              {m.role === 'ai' && m.citations && m.citations.length > 0 && (
                <div className="mt-3 text-xs text-gray-500 space-y-2">
                  <div className="font-medium text-gray-600 mb-1">Sources</div>
                  <div className="grid gap-2">
                    {m.citations.map((c: any, idx: number) => (
                      <div key={idx} className="bg-gray-50 border border-gray-100 p-2 rounded text-sm">
                        <div className="flex justify-between">
                          <div className="font-mono text-xs text-blue-700">Chunk {c.chunk_index}</div>
                          <div className="text-xs text-gray-400">Relevance: {c.score.toFixed(3)}</div>
                        </div>
                        <div className="text-sm text-gray-600 mt-1 line-clamp-2">“{c.text}”</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex items-center gap-3 text-blue-600 font-medium px-1">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
            <span className="text-sm">Searching vectors & generating answer...</span>
          </div>
        )}

        {error && (
          <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-100">{error}</div>
        )}
      </div>

      {/* Input area */}
      <div className="p-4 bg-white border-t border-gray-100">
        <form onSubmit={handleSubmit} className="relative">
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            // Keep the input editable during generation; users can type while the model generates
            disabled={false}
            placeholder={editingMessageId ? 'Edit your message and press Enter to resubmit' : 'e.g., What is Principal Component Analysis?'}
            className="w-full pl-4 pr-40 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
          />

          {/* Stop Generating button (visible while loading) */}
          {isLoading && (
            <button
              type="button"
              onClick={() => {
                try {
                  abortControllerRef.current?.abort();
                } catch (err) {
                  console.error('Failed to abort generation:', err);
                }
              }}
              className="absolute right-24 top-2 bottom-2 px-3 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium mr-2"
            >
              Stop
            </button>
          )}

          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="absolute right-2 top-2 bottom-2 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white font-medium rounded-lg transition-colors"
          >
            {editingMessageId ? 'Update' : 'Ask'}
          </button>
        </form>
      </div>
    </div>
  );
}