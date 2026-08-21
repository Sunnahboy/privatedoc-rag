from uuid import uuid4


def generate_document_id() -> str:
    """
    Generate a unique document ID.
    Why not use the original filename?
    - Filenames can repeat.
    - Filenames may contain unsafe characters.
    - Internal IDs should be stable and unique.
    """
    return f"doc_{uuid4().hex}"

def generate_chunk_id(document_id: str, chunk_index: int) -> str:
    """
    Generate a deterministic chunk ID based on the parent document.
    Makes it easy to query PostgreSQL/Qdrant for 'all chunks in doc X'.
    """
    return f"{document_id}_chunk_{chunk_index}"
