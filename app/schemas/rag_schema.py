from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str


class CitationResponse(BaseModel):
    document_id: str
    chunk_index: int
    text: str
    score: float


class AskResponse(BaseModel):
    answer: str
    citations: list[CitationResponse]
