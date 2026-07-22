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

    chunk_id: str
    document_id:str
    chunk_index:int
    text: str
    start_char: int
    end_char: int
    metadata:dict[str,any]
