from dataclasses import dataclass

from app.pipeline.retrieval.models import RetrievedChunk


@dataclass(slots=True)
class GenerateResult:
    answer: str
    citations: list[RetrievedChunk]
    prompt_tokens: int
    completion_tokens: int
    prompt_chars: int
