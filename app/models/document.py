from datetime import datetime, timezone

from app.database import Base
from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column


def utc_now() -> datetime:
    """
    Return timezone aware utc datetime.
     Why:
    - Server timezones vary.
    - UTC timestamps are easier to compare and debug.
    """

    return datetime.now(timezone.utc)


class Document(Base):
    """
    SQLAlchemy ORM model for uploaded document metadata.

    This table does not store the raw PDF/file bytes.
    It stores facts about the file and where the file lives.

    """

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(20), nullable=False)
    file_size_bytes: Mapped[str] = mapped_column(BigInteger, nullable=False)

    storage_provider: Mapped[str] = mapped_column(
        String(50), default="local", nullable=False
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)

    status: Mapped[str] = mapped_column(String(50), default="uploaded", nullable=False)

    total_pages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_chunks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
