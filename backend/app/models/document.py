import enum
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Enum,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    """
    Return timezone aware utc datetime.
     as:
    - Server timezones vary.
    - UTC timestamps are easier to compare and debug.
    """

    return datetime.now(UTC)


class IngestStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING_TEXT = "PROCESSING_TEXT"
    PROCESSING_VISUAL = "PROCESSING_VISUAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Document(Base):
    """
    SQLAlchemy ORM model for uploaded document metadata.

    This table does not store the raw PDF/file bytes.
    It stores facts about the file and where the file lives.

    """

    __tablename__ = "documents"
    __table_args__ = (
        # A content hash is unique only within one tenant. This permits two
        # users to upload identical files without sharing document ownership.
        UniqueConstraint(
            "user_id",
            "content_hash",
            name="uq_documents_user_content_hash",
        ),
    )

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    # Every document belongs to exactly one authenticated tenant.
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(20), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Deduplication & Storage
    content_hash: Mapped[str] = mapped_column(
        String(64), index=True, nullable=False
    )

    storage_provider: Mapped[str] = mapped_column(
        String(50), default="local", nullable=False
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)

    # Pipeline State Tracking
    status: Mapped[IngestStatus] = mapped_column(
        Enum(IngestStatus), default=IngestStatus.QUEUED, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, default=dict, nullable=True
    )
    # Document Structure Metadata
    total_pages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_chunks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    toc: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
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
