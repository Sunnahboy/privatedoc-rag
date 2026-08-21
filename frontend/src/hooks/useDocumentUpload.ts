import { useState } from "react";
import { apiClient, DocumentListItem, normalizeDocumentStatus } from "@/lib/api-client";
import { UPLOAD_POLLING_INTERVAL_MS } from "@/lib/constants";
export type UploadState = "idle" | "uploading" | "polling" | "success" | "error";

export function useDocumentUpload(onSuccess?:()=>void) {
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
                    const normalizedStatus = normalizeDocumentStatus(latestDoc.status);
                    setDocument({ ...latestDoc, status: normalizedStatus });

                    if (normalizedStatus === "indexed") {
                        setStatus("success");
                        clearInterval(pollInterval);
                        if (onSuccess) {
                            onSuccess();
                        }

                        setTimeout(() => {
                            setStatus("idle");
                            setDocument(null);
                        }, 2000);
                    } else if (normalizedStatus === "failed") {
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