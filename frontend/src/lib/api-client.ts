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
}

export interface RagResponse {
    session_id: string;
    answer: string;
    citations: Citation[];
}

export interface ChatMessage {
    id: string;
    session_id: string;
    role: "user" | "assistant";
    content: string;
    citations: Citation[];
    created_at: string;
}

// Stream chunk event types matching our SSE backend
export type StreamChunk =
    | { type: "session"; session_id: string }
    | { type: "status"; stage: "retrieval" | "generation"; message: string }
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
     * Sends a RAG query to the backend and streams the response via SSE.
     */
    async askQuestionStream(
        query: string,
        documentIds?: string[],
        sessionId?: string | null,
        onChunk?: (chunk: StreamChunk) => void,
        signal?: AbortSignal
    ): Promise<void> {
        const payload = {
            question: query,
            document_id: documentIds && documentIds.length > 0 ? documentIds[0] : null,
            session_id: sessionId || null,
        };

        const response = await fetch(`${API_BASE_URL}/rag/ask`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
            signal,
        });

        if (!response.ok || !response.body) {
            throw new Error(`Failed to start stream: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const parts = buffer.split("\n\n");
            buffer = parts.pop() || "";

            for (const part of parts) {
                const trimmed = part.trim();
                if (trimmed.startsWith("data: ")) {
                    const jsonStr = trimmed.replace("data: ", "").trim();
                    try {
                        const parsed: StreamChunk = JSON.parse(jsonStr);
                        if (onChunk) {
                            onChunk(parsed);
                        }
                    } catch (e) {
                        console.error("Failed to parse SSE line:", jsonStr, e);
                    }
                }
            }
        }
    },

    /**
     * Non-streaming fallback if needed
     */
    async askQuestion(query: string, documentIds?: string[], sessionId?: string | null, signal?: AbortSignal): Promise<RagResponse> {
        const payload = {
            question: query,
            document_id: documentIds && documentIds.length > 0 ? documentIds[0] : null,
            session_id: sessionId || null,
        };

        const response = await fetch(`${API_BASE_URL}/rag/ask`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
            signal,
        });

        if (!response.ok) {
            throw new Error(`Failed to generate answer: ${response.status}`);
        }

        return response.json();
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

    async truncateChatHistory(sessionId: string, messageId: string): Promise<void> {
        const response = await fetch(`${API_BASE_URL}/chat/sessions/${sessionId}/messages/${messageId}`, {
            method: "DELETE",
        });

        if (!response.ok) {
            throw new Error(`Failed to truncate history: ${response.status}`);
        }
    },
};