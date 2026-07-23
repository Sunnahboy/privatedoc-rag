from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class EmbeddingResult:
    """
    Output of every embedding model.

    """

    chunk_id: str
    document_id: str
    chunk_index: int
    vector: list[float]
    model_name: str
    dimensionsL: int
    metadata: dict[str, Any] = field(default_factory=dict)
