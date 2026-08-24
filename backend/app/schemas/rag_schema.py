from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str
    document_id: str | None = None
    session_id: str | None = None


class CitationResponse(BaseModel):
    document_id: str
    chunk_index: int
    text: str
    score: float


class AskResponse(BaseModel):
    session_id: str
    answer: str
    citations: list[CitationResponse]
