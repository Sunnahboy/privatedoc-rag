
from pydantic import BaseModel, Field

class DocumentIngestMessage(BaseModel):
    """Payload schema for document ingestion jobs."""

    document_id: str = Field(..., description="Unique database document identifier")
    storage_key: str = Field(..., description="Filename/key where the file is saved")
class ChatGenerationMessage(BaseModel):
    message_id: str
    session_id: str
    question: str
    document_ids: list[str] = []
