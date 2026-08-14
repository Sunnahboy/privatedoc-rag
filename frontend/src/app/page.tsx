"use client";

import { useState } from "react";
import { FileUploader } from "@/components/upload/FileUploader";
import { RagChat } from "@/components/chat/RagChat";
import { DocumentList } from "@/components/documents/DocumentList";
import { useDocuments } from "@/hooks/useDocuments";
export default function Home() {
  const { documents, isLoading, fetchDocuments, deleteDocument } = useDocuments();
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);

  const toggleSelection = (id: string) => {
    setSelectedDocIds(prev => 
      prev.includes(id) ? prev.filter(docId => docId !== id) : [...prev, id]
    );
  };

  return (
    <main className="min-h-screen p-8 bg-gray-50 text-gray-900">
      <div className="max-w-6xl mx-auto">
        
        <header className="text-center mb-12">
          <h1 className="text-4xl font-extrabold tracking-tight text-gray-900">
            PrivateDoc <span className="text-blue-600">RAG</span>
          </h1>
          <p className="text-gray-500 mt-2 text-lg">Local document intelligence & embedding search</p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Left Column: Upload & Document List */}
          <div className="lg:col-span-1 space-y-6">
            <section className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
              <h2 className="text-lg font-bold mb-4 text-gray-800">Add Knowledge</h2>
              {/* Pass fetchDocuments so Uploader can refresh the list when done */}
              <FileUploader onUploadComplete={fetchDocuments} />
            </section>

            <section className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-bold text-gray-800">Your Documents</h2>
                {selectedDocIds.length > 0 && (
                  <button onClick={() => setSelectedDocIds([])} className="text-xs text-blue-600 hover:underline">
                    Clear Selection
                  </button>
                )}
              </div>
              <DocumentList 
                documents={documents} 
                isLoading={isLoading} 
                selectedIds={selectedDocIds}
                onToggleSelection={toggleSelection}
                onDeleteDocument={deleteDocument}
              />
            </section>
          </div>

          {/* Right Column: Chat */}
          <div className="lg:col-span-2">
            <RagChat />
          </div>

        </div>
      </div>
    </main>
  );
}