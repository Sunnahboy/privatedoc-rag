import onnxruntime as ort
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application configuration.

    Why this exists:
    - Real systems should not hardcode ports, model names, database URLs, or paths.
    - Environment variables let the same code run locally, in Docker, and on a server.
    """

    app_name: str = "PrivateDoc RAG"
    app_version: str = "0.1.0"
    environment: str = "development"

    # Upload settings
    upload_dir: str = "../data/uploads"
    max_upload_mb: int = 300
    allowed_file_extensions: str = ".pdf,.txt,.md,.ppt,.docx"
    file_stream_chunk_size_bytes: int = 1024 * 1024  # 1MB

    # Metadata database
    database_url: str = "sqlite+aiosqlite:///./privatedoc.db"
    database_echo: bool = False

    # Extraction & OCR settings
    pdf_ocr_dpi: int = 72
    min_digital_text_words: int = 15
    pdf_ocr_max_concurrent: int = (
        4 if "CUDAExecutionProvider" in ort.get_available_providers() else 2
    )
    # Retrieval & Reranker settings
    rrf_k: int = 60
    top_k_reranker: int = 5
    reranker_model: str = "ms-marco-MiniLM-L-12-v2"
    reranker_enabled: bool = True

    # RAG services (Qdrant & Ollama)
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection_name: str = "documents"

    ollama_url: str = "http://localhost:11434"
    embedding_provider: str = "ollama"
    embedding_model: str = "nomic-embed-text"
    embedding_dimensions: int = 768
    embedding_timeout: int = 30
    embedding_max_concurrency: int = 2
    embedding_batch_size: int = 16

    generation_model: str = "llama3.1:8b"
    generation_timeout: int = 60

    qdrant_max_concurrent_requests: int = 8
    qdrant_batch_size: int = 64
    retrieval_score_threshold: float = 0.5
    hybrid_candidate_multiplier: int = 2

    top_k_search: int = 5
    chunking_strategy: str = "recursive"
    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 100
    tantivy_index_path: str = "./data/tantivy"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @computed_field
    @property
    def allowed_extensions_set(self) -> set[str]:
        """
        Convert comma separated extensions into a python set.
        Runs only once at startup.
        """
        return {
            ext.strip().lower()
            for ext in self.allowed_file_extensions.split(",")
            if ext.strip()
        }

    @computed_field
    @property
    def max_upload_bytes(self) -> int:
        """Convert MB to bytes for file limit validations."""
        return self.max_upload_mb * 1024 * 1024


settings = Settings()
