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


export interface DocumentUploadResponse{
    document_id: string;
    filename:string;
    original_filename:string;
    status:string;

}

export interface DocumentListItem{
    document_id:string;
    filename:string;
    original_filename: string;
    status:string;
    total_chunks:number; //pending processing indexed failed
    total_pages:number;
}
export interface Citation{
    document_id:string;
    chunk_index: number;
    text:string;
    score:number;
}

export interface RagResponse{
    session_id: string;
    answer:  string;
    citations:Citation[];
}
// ChatMessage interface for history
export interface ChatMessage {
    id: string;
    session_id: string;
    role: "user" | "assistant";
    content: string;
    citations: Citation[];
    created_at: string;
}


export const  apiClient ={
    async uploadDocument(file:File): Promise<DocumentUploadResponse>{
        const formData = new FormData();
        formData.append("file",file);

        const response = await fetch(`${API_BASE_URL}/document/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok){
        const errorData =  await response.json().catch(() => null);
        throw new Error(errorData?.detail || `Upload failed with status ${response.status}`);
    }
    return response.json();

    },
    /**
     * Fetches the current processing status of a document.
     *  polls this endpoint while the RabbitMQ worker processes the file.
     */
    async getDocument(documentId: string): Promise<DocumentListItem>{
        const response = await fetch(`${API_BASE_URL}/document/${documentId}`);
        if(!response.ok){
            throw new Error(`Failed to fetch document status: ${response.status}`);
        }
        return response.json();
    },

    
    /**
   * Sends a RAG query to the backend.
   */
  async askQuestion(query: string, documentIds?: string[],sessionId?: string | null, signal?: AbortSignal): Promise<RagResponse> {
    
    // Translate frontend state into the exact backend schema
    const payload = {
      question: query,
      // If the user selected multiple docs,  pass the first one for now
      // since the backend currently only expects a single string
      document_id: documentIds && documentIds.length > 0 ? documentIds[0] : null,
      session_id: sessionId || null // Send to backend
    };

    const response = await fetch(`${API_BASE_URL}/rag/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload), // Send the translated payload
      signal,
    });

    if (!response.ok) {
      throw new Error(`Failed to generate answer: ${response.status}`);
    }

    return response.json();
  }, 
   /**
   * Fetches all uploaded documents from the database.
   */
    async listDocuments(): Promise<DocumentListItem[]> {
        const response = await fetch(`${API_BASE_URL}/document`);

        if (!response.ok){
                    throw new Error(`Failed to fetch documents: ${response.status}`);
        }
        return response.json();
    },

    /**
     * Deletes a document from the database, Qdrant, Tantivy, and the local disk.
     */
    async deleteDocument(documentId: string): Promise<void> {
        const response = await fetch(`${API_BASE_URL}/document/${documentId}`, {
            method: "DELETE",
        });

        if (!response.ok) {
            throw new Error(`Failed to delete document: ${response.status}`);
        }
    },

    //fetch chat history from the DB
    async getChatHistory(sessionId: string): Promise<ChatMessage[]> {
        const response = await fetch(`${API_BASE_URL}/chat/sessions/${sessionId}/messages`);
        
        if (!response.ok) {
            throw new Error(`Failed to fetch chat history: ${response.status}`);
        }
        
        return response.json();
    },

    /**
     * Deletes a message and all subsequent messages in a session.
     */
    async truncateChatHistory(sessionId: string, messageId: string): Promise<void> {
        const response = await fetch(`${API_BASE_URL}/chat/sessions/${sessionId}/messages/${messageId}`, {
            method: "DELETE",
        });

        if (!response.ok) {
            throw new Error(`Failed to truncate history: ${response.status}`);
        }
    }

};