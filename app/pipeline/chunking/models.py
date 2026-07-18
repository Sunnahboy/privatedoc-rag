from dataclasses import dataclass


@dataclass(slots=True)
class Chunk:
    """
    One searchable piece of a document

    This object eventually become:
     -PostgreSQL row
     -Qdrant vector
     -Citation source
    """

    Chunk_id: str
    text: str
    start_char: int
    end_char: int
