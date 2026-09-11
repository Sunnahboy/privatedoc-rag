import { API_BASE_URL } from "./constants";

export type DocumentStatus = "indexed" | "processing" | "failed";

export function normalizeDocumentStatus(status?: string | null): DocumentStatus {
    const normalized = status?.toString().trim().toLowerCase();

    if (!normalized) {
        return "processing";
    }

    if (normalized === "indexed" || normalized === "completed") {
        return "indexed";
    }

    if (normalized === "failed") {
        return "failed";
    }

    return "processing";
}

export interface DocumentUploadResponse {
    document_id: string;
    filename: string;
    original_filename: string;
    status: string;
}

export interface DocumentListItem {
    document_id: string;
    filename: string;
    original_filename: string;
    status: string;
    total_chunks: number;
    total_pages: number;
}

export interface Citation {
    document_id: string;
    chunk_index: number;
    text: string;
    score: number;
    page_number: number | null;
}

export interface RagResponse {
    session_id: string;
    answer: string;
    citations: Citation[];
}

export type ChatScopeType = "THIS_DOCUMENT" | "SELECTED_DOCUMENTS" | "ALL_DOCUMENTS";

export interface ChatSessionSummary {
    id: string;
    title: string | null;
    scope_type: ChatScopeType;
    document_ids: string[];
    is_pinned: boolean;
    created_at: string;
}

export interface ChatMessage {
    id: string;
    session_id: string;
    role: "user" | "assistant";
    content: string;
    citations: Citation[];
    created_at: string;
    status?: string;}//track message status
// new POST response
export interface ChatJobResponse {
    session_id: string;
    user_message_id: string;
    assistant_message_id: string;
}

const CHAT_SUBMISSION_TIMEOUT_MS = 30_000;

// Stream chunk event types matching our SSE backend
export type StreamChunk =
    | { type: "session"; session_id: string }
    | { type: "status"; stage?: "retrieval" | "generation"; message: string }
    | { type: "token"; content: string }
    | { type: "done"; citations: Citation[]; prompt_tokens?: number; completion_tokens?: number; prompt_chars?: number }
    | { type: "error"; error: string };

export const apiClient = {
    async uploadDocument(file: File): Promise<DocumentUploadResponse> {
        const formData = new FormData();
        formData.append("file", file);

        const response = await fetch(`${API_BASE_URL}/document/upload`, {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => null);
            throw new Error(errorData?.detail || `Upload failed with status ${response.status}`);
        }
        return response.json();
    },

    async getDocument(documentId: string): Promise<DocumentListItem> {
        const response = await fetch(`${API_BASE_URL}/document/${documentId}`);
        if (!response.ok) {
            throw new Error(`Failed to fetch document status: ${response.status}`);
        }
        return response.json();
    },

    /**
     * The Producer (Fire and Forget)
     * Submits the query to the backend, which instantly returns DB records and queues the worker.
     */
    async submitChatJob(
        query: string,
        documentIds: string[],
        sessionId?: string | null,
        signal?: AbortSignal,
    ): Promise<ChatJobResponse> {
        if (signal?.aborted) {
            throw new DOMException("Aborted", "AbortError");
        }

        const payload = {
            question: query,
            document_ids: documentIds,
            session_id: sessionId || null,
        };

        // A queued request must never leave the composer blocked forever.
        // Use a local controller so the user can cancel it, while also
        // surfacing a clear error if the API does not respond in time.
        const controller = new AbortController();
        let timedOut = false;
        const timeoutId = window.setTimeout(() => {
            timedOut = true;
            controller.abort();
        }, CHAT_SUBMISSION_TIMEOUT_MS);
        const abortFromCaller = () => controller.abort();
        signal?.addEventListener("abort", abortFromCaller, { once: true });

        try {
            const response = await fetch(`${API_BASE_URL}/rag/ask`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(payload),
                signal: controller.signal,
            });

            if (!response.ok) {
                throw new Error(`Failed to submit chat job: ${response.status}`);
            }

            return response.json();
        } catch (error) {
            if (timedOut) {
                throw new Error("Chat submission timed out. Please try again.");
            }
            throw error;
        } finally {
            window.clearTimeout(timeoutId);
            signal?.removeEventListener("abort", abortFromCaller);
        }
    },

    // src/lib/api-client.ts

    async streamChatResponse(
        assistantMessageId: string,
        onChunk: (chunk: StreamChunk) => void,
        signal?: AbortSignal,
        onReplayStart?: () => void
    ): Promise<void> {
        return new Promise<void>((resolve, reject) => {
            if (signal && signal.aborted) {
                return reject(new DOMException("Aborted", "AbortError"));
            }

            // THE FIX: The backend now always replays the full buffered
            // history from the start on every (re)connect, so we no longer
            // track/send a fragile last_offset via localStorage.
            const url = `${API_BASE_URL}/rag/stream/${assistantMessageId}`;
            const eventSource = new EventSource(url);

            if (signal) {
                signal.addEventListener("abort", () => {
                    eventSource.close();
                    reject(new DOMException("Aborted", "AbortError"));
                });
            }

            // THE FIX: Every (re)connection - including the browser's native
            // auto-reconnect after a dropped connection - triggers a full
            // replay from offset 0. Without resetting local accumulator
            // state here, reconnects would duplicate already-appended
            // tokens. onReplayStart lets the caller reset its buffer right
            // before the replayed events start arriving.
            eventSource.onopen = () => {
                onReplayStart?.();
            };

            eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    onChunk(data);

                    if (data.type === "done" || data.type === "error") {
                        eventSource.close();
                        resolve();
                    }
                } catch (err) {
                    console.error("Failed to parse SSE chunk", err);
                }
            };

            eventSource.onerror = (err) => {
                console.warn("SSE Connection issue. Browser will attempt to reconnect natively...", err);
            };
        });
    },

    async listDocuments(): Promise<DocumentListItem[]> {
        const response = await fetch(`${API_BASE_URL}/document`);
        if (!response.ok) {
            throw new Error(`Failed to fetch documents: ${response.status}`);
        }
        return response.json();
    },

    async deleteDocument(documentId: string): Promise<void> {
        const response = await fetch(`${API_BASE_URL}/document/${documentId}`, {
            method: "DELETE",
        });

        if (!response.ok) {
            throw new Error(`Failed to delete document: ${response.status}`);
        }
    },

    async getChatHistory(sessionId: string): Promise<ChatMessage[]> {
        const response = await fetch(`${API_BASE_URL}/chat/sessions/${sessionId}/messages`);
        if (!response.ok) {
            throw new Error(`Failed to fetch chat history: ${response.status}`);
        }
        return response.json();
    },

    async listChatSessions(): Promise<ChatSessionSummary[]> {
        const response = await fetch(`${API_BASE_URL}/chat/sessions`);
        if (!response.ok) {
            throw new Error(`Failed to fetch chat sessions: ${response.status}`);
        }
        return response.json();
    },

    async createChatSession(
        scopeType: ChatScopeType,
        documentIds: string[],
    ): Promise<ChatSessionSummary> {
        const response = await fetch(`${API_BASE_URL}/chat/sessions`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ scope_type: scopeType, document_ids: documentIds }),
        });

        if (!response.ok) {
            throw new Error(`Failed to create chat session: ${response.status}`);
        }
        return response.json();
    },

    async deleteChatSession(sessionId: string): Promise<void> {
        // NOTE: session-level delete lives under /rag/sessions/{id} (not /chat/sessions/{id}) -
        // /chat/sessions/{id} is reserved for per-message truncation.
        const response = await fetch(`${API_BASE_URL}/rag/sessions/${sessionId}`, {
            method: "DELETE",
        });

        if (!response.ok) {
            throw new Error(`Failed to delete chat session: ${response.status}`);
        }
    },

    async updateChatSession(
        sessionId: string,
        updates: { title?: string; is_pinned?: boolean },
    ): Promise<ChatSessionSummary> {
        const response = await fetch(`${API_BASE_URL}/chat/sessions/${sessionId}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(updates),
        });

        if (!response.ok) {
            throw new Error(`Failed to update chat session: ${response.status}`);
        }
        return response.json();
    },

    async truncateChatHistory(sessionId: string, messageId: string): Promise<void> {
        const response = await fetch(`${API_BASE_URL}/chat/sessions/${sessionId}/messages/${messageId}`, {
            method: "DELETE",
        });

        if (!response.ok) {
            throw new Error(`Failed to truncate history: ${response.status}`);
        }
    },
};
