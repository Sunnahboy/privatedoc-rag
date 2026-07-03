from uuid import uuid4

def generate_document_id() -> str:
    """
    Generate a unique document ID.
    Why not use the original filename?
    - Filenames can repeat.
    - Filenames may contain unsafe characters.
    - Internal IDs should be stable and unique.
    """
    return f"doc_{uuid4()}.hex"