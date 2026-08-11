import hashlib
from pathlib import Path

from fastapi import UploadFile

from app.config import settings


def calculate_file_hash(
    file_path: str | Path,
) -> str:
    """
    Computes the SHA-256 hash of an existing disk file using optimized C-level chunking.

    """

    path = Path(file_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Cannot hash missing file: {path}")
    with path.open("rb") as f:
        digest = hashlib.file_digest(
            f, "sha256", _bufsize=settings.file_stream_chunk_size_bytes
        )

    return digest.hexdigest()


async def calculate_upload_stream_hash(file: UploadFile) -> str:
    """
    Computes the SHA-256 hash of an incoming FastAPI UploadFile stream in memory.

    Maintains low memory usage via chunking. Automatically resets the stream
    pointer to 0 so the file can be read or saved downstream afterward.
    """
    sha256 = hashlib.sha256()
    chunk_size = settings.file_stream_chunk_size_bytes

    try:
        #Read the stream in chunks until EOF to compute the hash
        while chunk := await file.read(chunk_size):
            sha256.update(chunk)

        return sha256.hexdigest()

    finally:
        await file.seek(0)
