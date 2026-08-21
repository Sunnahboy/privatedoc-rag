// API Configuration
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Upload Configuration
export const UPLOAD_POLLING_INTERVAL_MS = 3000;
export const MAX_FILE_SIZE_MB = 300;
export const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

// UI Messages
export const ERROR_MESSAGES = {
  UPLOAD_FAILED: "The background worker failed to process this document.",
  NETWORK_ERROR: "Failed to connect to the server. Please check your network.",
  FILE_TOO_LARGE: `File exceeds the maximum limit of ${MAX_FILE_SIZE_MB}MB.`,
} as const; 
