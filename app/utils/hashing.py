import hashlib
from pathlib import Path

from app.config import settings


def calculate_file_hash(
    file_path: str | Path,
) -> str:
    """
    Computes the SHA-256 hash of a file efficiently by reading it in chunks.

    Args:
        file_path: Path to the file.
        chunk_size: Number of bytes to read per iteration (prevents memory spikes).

    Returns:
        The hex digest of the SHA-256 hash.
    """

    path = Path(file_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Cannot hash missing file: {path}")
    with path.open("rb") as f:
        digest = hashlib.file_digest(
            f, "sha256", _bufsize=settings.file_stream_chunk_size_bytes
        )

    return digest.hexdigest()
