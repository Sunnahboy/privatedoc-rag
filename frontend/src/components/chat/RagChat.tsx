"use client";

import { useRAGQuery } from "@/hooks/useRAGQuery";
import ReactMarkdown from 'react-markdown';
export function RagChat({ selectedDocIds }: { selectedDocIds: string[] }) {
  const { query, setQuery, isLoading, response, error, askQuestion, clearChat } = useRAGQuery();

  return (
    <div className="w-full bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden flex flex-col `h-150`">
      
      {/* 1. Header */}
      <div className="bg-gray-50 border-b border-gray-100 p-4 flex justify-between items-center">
        <h2 className="font-semibold text-gray-800">Ask Your Documents</h2>

        {/* Only show the Clear button if there is a response or a typed query */}
        {(response || query) && (
          <button 
            onClick={clearChat}
            disabled={isLoading}
            className="text-xs font-medium text-gray-500 hover:text-gray-900 bg-white border border-gray-200 hover:bg-gray-100 px-3 py-1 rounded transition-colors disabled:opacity-50"
          >
            Clear Chat
          </button>
        )}
      </div>

      {/* 2. Scrollable Output Area */}
      <div className="flex-1 overflow-y-auto p-6 bg-gray-50/50">
        {!response && !isLoading && !error && (
          <div className="h-full flex items-center justify-center text-gray-400">
            Ask a question to search your indexed documents.
          </div>
        )}

       
        {isLoading && (
          <div className="space-y-6 animate-pulse">
            {/* Loading Status Indicator */}
            <div className="flex items-center gap-3 text-blue-600 font-medium px-1">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
              <span className="text-sm">Searching vectors & generating answer...</span>
            </div>

            {/* Answer Skeleton */}
            <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm">
              <div className="h-3 bg-gray-200 rounded w-20 mb-4"></div>
              <div className="space-y-3">
                <div className="h-4 bg-gray-200 rounded w-full"></div>
                <div className="h-4 bg-gray-200 rounded w-[90%]"></div>
                <div className="h-4 bg-gray-200 rounded w-[95%]"></div>
                <div className="h-4 bg-gray-200 rounded w-[75%]"></div>
              </div>
            </div>

            {/* Citations Skeleton */}
            <div>
              <div className="h-3 bg-gray-200 rounded w-20 mb-3"></div>
              <div className="grid gap-3">
                {[1, 2, 3].map((skeletonIdx) => (
                  <div key={skeletonIdx} className="bg-white p-4 rounded-lg border border-gray-100 shadow-sm">
                    <div className="flex justify-between items-start mb-3">
                      <div className="h-5 bg-gray-200 rounded w-20"></div>
                      <div className="h-3 bg-gray-200 rounded w-24"></div>
                    </div>
                    <div className="space-y-2">
                      <div className="h-3 bg-gray-200 rounded w-full"></div>
                      <div className="h-3 bg-gray-200 rounded w-[85%]"></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-100">
            {error}
          </div>
        )}

        {response && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
            {/* The Answer */}
            <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm">
              <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-3">Answer</h3>
              
              <div className="prose prose-blue prose-sm sm:prose-base max-w-none text-gray-800">
                <ReactMarkdown>
                  {response.answer}
                </ReactMarkdown>
              </div>
            </div>

            {/* The Citations */}
            <div>
              <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-3">Sources</h3>
              <div className="grid gap-3">
                {response.citations.map((citation, idx) => (
                  <div key={idx} className="bg-white p-4 rounded-lg border border-gray-200 text-sm">
                    <div className="flex justify-between items-start mb-2">
                      <span className="font-medium text-blue-700 font-mono text-xs bg-blue-50 px-2 py-1 rounded">
                        Chunk {citation.chunk_index}
                      </span>
                      <span className="text-xs text-gray-400 font-mono">
                        Relevance: {citation.score.toFixed(3)}
                      </span>
                    </div>
                    <p className="text-gray-600 line-clamp-3 hover:line-clamp-none transition-all cursor-pointer">
“{citation.text}”
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 3. Input Area */}
      <div className="p-4 bg-white border-t border-gray-100">
       <form onSubmit={(e) => askQuestion(e, selectedDocIds)} className="relative">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={isLoading}
            placeholder="e.g., What is Principal Component Analysis?"
            className="w-full pl-4 pr-24 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="absolute right-2 top-2 bottom-2 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white font-medium rounded-lg transition-colors"
          >
            Ask
          </button>
        </form>
      </div>
    </div>
  );
}