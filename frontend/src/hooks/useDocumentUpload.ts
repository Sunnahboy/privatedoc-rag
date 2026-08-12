import { useState } from "react";
import { apiClient, DocumentListItem } from "@/lib/api-client";
import { UPLOAD_POLLING_INTERVAL_MS, ERROR_MESSAGES } from "@/lib/constants";
export type UploadState = "idle" | "uploading" | "polling" | "success" | "error";

export function useDocumentUpload() {
    const [status, setStatus] = useState<UploadState>("idle");
    const [document, setDocument] = useState<DocumentListItem | null>(null);
    const [error, setError] = useState<string | null>(null);

    const uploadFile = async (file: File) => {
        try {
            setStatus("uploading");
            setError(null);

            // start polling the worker's progress every 3 seconds
            const uploadRes = await apiClient.uploadDocument(file);
            setStatus("polling");
            const pollInterval = setInterval(async () => {
                try {
                    const latestDoc = await apiClient.getDocument(uploadRes.document_id);
                    setDocument(latestDoc);
                    // stop polling when the worker finishes
                    if (latestDoc.status === "indexed") {
                        setStatus("success");
                        clearInterval(pollInterval);
                    } else if (latestDoc.status === "failed") {
                        setStatus("error");
                        setError("The background worker failed to process this document.");
                        clearInterval(pollInterval);
                    }
                } catch (pollErr) {
                    console.error("Polling error (will retry:", pollErr);
                }
            }, UPLOAD_POLLING_INTERVAL_MS);
        } catch (err: unknown) {
            setStatus("error");
            setError(err instanceof Error ? err.message : "Failed to upload file.");
        }
    };
        const reset = () => {
            setStatus("idle");
            setDocument(null);
            setError(null);

    };
    return {status, document, error, uploadFile, reset};

}