from dataclasses import dataclass, field


@dataclass(slots=True)
class Chunk:
    """
    One searchable piece of a document

    This object eventually become:
     -PostgreSQL row
     -Qdrant vector
     -Citation source
    """

    chunk_id: str
    document_id: str
    chunk_index: int
    text: str
    start_char: int
    end_char: int
    page_number: int | None = None
    metadata: dict[str, any] = field(default_factory=dict)
