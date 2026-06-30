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

    upload_dir: str = "../data/uploads"

    qdrant_url: str = "http://localhost:6333"
    ollama_url: str = "http://localhost:11434"

    embedding_model: str = "nomic-embed-text"
    generation_model: str = "llama3.1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()