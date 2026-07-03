from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field

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
    max_upload_mb:str = 20
    allowed_file_extensions:str = ".pdf,.txt,.md,.ppt"

    #future RAG services
    qdrant_url: str = "http://localhost:6333"
    ollama_url: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text"
    generation_model: str = "llama3.1"
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @computed_field
    @property
    def allowed_extensions_set(self)->set[str]:
        """
         Convert comma separated extensions into a python set.
         Runs only once at startup
        
         example:
          ".pdf,.txt,.md,.ppt" -> {".pdf",".txt",".md",".ppt"}

          why:
            - Set lookup is clean and fast.
            - It keeps validation logic out of the route
        """
        return{
            ext.strip().lower()
            for ext in self.allowed_extensions.split(",")
            if ext.strip()

        }
    
    @computed_field
    @property
    def max_upload_bytes(self)->int:
        """
        Convert MB to bytes.
         
        why:
            - uploaded files are measured in bytes.
            - Humans prefer configuring files limits in MB
        """
        return self.max_upload_mb * 1024 * 1024

settings = Settings()