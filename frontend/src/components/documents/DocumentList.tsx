import { DocumentListItem } from "@/lib/api-client";

interface DocumentListProps {
  documents: DocumentListItem[];
  isLoading: boolean;
  selectedIds: string[];
  onToggleSelection: (id: string) => void;
  onDeleteDocument: (id: string) => void; // New Prop
}

export function DocumentList({ documents, isLoading, selectedIds, onToggleSelection, onDeleteDocument }: DocumentListProps) {
  if (isLoading) {
    return <div className="text-sm text-gray-500 animate-pulse">Loading documents...</div>;
  }

  if (documents.length === 0) {
    return <div className="text-sm text-gray-500">No documents indexed yet.</div>;
  }

  return (
    <div className="space-y-2 `max-h-100` overflow-y-auto pr-2">
      {documents.map((doc) => (
        <div 
          key={doc.document_id}
          className={`flex items-start gap-3 p-3 rounded-lg border transition-all ${
            selectedIds.includes(doc.document_id) 
              ? "bg-blue-50 border-blue-200" 
              : "bg-white border-gray-100 hover:border-gray-300"
          }`}
        >
          <input 
            type="checkbox" 
            className="mt-1 h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500 cursor-pointer"
            checked={selectedIds.includes(doc.document_id)}
            onChange={() => onToggleSelection(doc.document_id)}
          />
          <div 
            className="flex-1 min-w-0 cursor-pointer"
            onClick={() => onToggleSelection(doc.document_id)}
          >
            <p className="text-sm font-medium text-gray-900 truncate" title={doc.original_filename}>
              {doc.original_filename}
            </p>
            <div className="flex items-center gap-2 mt-1">
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                doc.status === 'indexed' ? 'bg-green-100 text-green-700' :
                doc.status === 'failed' ? 'bg-red-100 text-red-700' :
                'bg-yellow-100 text-yellow-700'
              }`}>
                {doc.status}
              </span>
              {doc.status === 'indexed' && (
                <span className="text-xs text-gray-500">{doc.total_chunks} chunks</span>
              )}
            </div>
          </div>
          
          {/* Delete Button */}
          <button 
            onClick={(e) => {
              e.stopPropagation(); // Prevents checking/unchecking the box
              e.preventDefault();
              if (window.confirm("Are you sure you want to delete this document?")) {
                onDeleteDocument(doc.document_id);
              }
            }}
            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
            title="Delete Document"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      ))}
    </div>
  );
}