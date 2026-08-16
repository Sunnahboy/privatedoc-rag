"use client"; // Tells Next.js this component uses browser features (hooks/events)

import { useRef, useEffect } from "react";
import { useDocumentUpload } from "@/hooks/useDocumentUpload";
import { MAX_FILE_SIZE_MB, MAX_FILE_SIZE_BYTES, ERROR_MESSAGES } from "@/lib/constants";

interface FileUploaderProps {
  onUploadComplete?: () => Promise<void> | void;
  compact?: boolean;
}

export function FileUploader({ onUploadComplete, compact = false }: FileUploaderProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  // Pass the parent's callback into the hook so it is triggered as soon as the uploader detects success
  const { status, document, error, uploadFile, reset } = useDocumentUpload(onUploadComplete);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Fail-fast check: stop before contacting backend if file is too large
      if (file.size > MAX_FILE_SIZE_BYTES) {
        alert(ERROR_MESSAGES.FILE_TOO_LARGE);
        return; // Stop right here, don't ping the backend
      }

      uploadFile(file);
    }
  };

  // Clear the native file input when the upload finishes successfully so the UI is fully reset
  useEffect(() => {
    if (status === "success") {
      try {
        if (fileInputRef.current) {
          // clearing a file input value is the supported way to reset its state
          fileInputRef.current.value = "";
        }
      } catch (err) {
        // Not fatal — continue and let parent re-fetch documents
        console.error("Failed to clear file input after upload success:", err);
      }
    }
  }, [status]);

  return (
    <div className="w-full">
      {/* 1. IDLE STATE: Show the dashed upload box */}
      {status === "idle" && (
        <div 
          onClick={() => fileInputRef.current?.click()}
          className={`cursor-pointer rounded-xl border-2 border-dashed border-gray-300 text-center transition-colors hover:bg-gray-50 ${
            compact ? "p-6" : "p-12"
          }`}
        >
          <input
            type="file"
            accept=".pdf"
            className="hidden"
            ref={fileInputRef}
            onChange={handleFileChange}
          />
          <div className="text-gray-500">
            <svg className={`mx-auto mb-4 text-gray-400 ${compact ? "h-8 w-8" : "h-12 w-12"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p className={`font-medium ${compact ? "text-base" : "text-lg"}`}>Click to upload a PDF</p>
            <p className="text-sm mt-1">Maximum file size {MAX_FILE_SIZE_MB}MB</p>
          </div>
        </div>
      )}

      {/* 2. UPLOADING & POLLING STATES: Show progress */}
      {(status === "uploading" || status === "polling") && (
        <div className="p-8 bg-blue-50 text-blue-700 rounded-xl flex flex-col items-center border border-blue-100">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-700 mb-4"></div>
          <p className="font-semibold text-lg">
            {status === "uploading" ? "Uploading to Server..." : "RabbitMQ is Processing Document..."}
          </p>
          <p className="text-sm mt-2 opacity-80">This may take a minute for large PDFs.</p>
        </div>
      )}

      {/* 3. SUCCESS STATE: Ready for RAG */}
      {status === "success" && document && (
        <div className="p-6 bg-green-50 text-green-800 rounded-xl border border-green-200">
          <div className="flex items-center gap-3 mb-2">
            <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <h3 className="font-bold text-lg">Document Ready!</h3>
          </div>
          <p><strong>{document.original_filename}</strong> was successfully indexed.</p>
          <p className="text-sm mt-1 opacity-80">Extracted {document.total_chunks} chunks across {document.total_pages} pages.</p>
          <button onClick={reset} className="mt-4 px-4 py-2 bg-white text-green-700 rounded shadow-sm border border-green-200 hover:bg-green-100 font-medium transition-colors">
            Upload Another
          </button>
        </div>
      )}

      {/* 4. ERROR STATE */}
      {status === "error" && (
        <div className="p-6 bg-red-50 text-red-700 rounded-xl border border-red-200">
          <h3 className="font-bold text-lg mb-1">Upload Failed</h3>
          <p>{error}</p>
          <button onClick={reset} className="mt-4 px-4 py-2 bg-white text-red-700 rounded shadow-sm border border-red-200 hover:bg-red-100 font-medium transition-colors">
            Try Again
          </button>
        </div>
      )}
    </div>
  );
}