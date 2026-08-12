import { API_BASE_URL } from "./constants";

// ... rest of the file stays the same
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
    answer:  string;
    citations:Citation[];
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
     * We will poll this endpoint while the RabbitMQ worker processes the file.
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
  async askQuestion(query: string, documentIds?: string[]): Promise<RagResponse> {
    
    // Translate frontend state into the exact backend schema
    const payload = {
      question: query,
      // If the user selected multiple docs, just pass the first one for now
      // since the backend currently only expects a single string
      document_id: documentIds && documentIds.length > 0 ? documentIds[0] : null
    };

    const response = await fetch(`${API_BASE_URL}/rag/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload), // Send the translated payload
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
    }

};