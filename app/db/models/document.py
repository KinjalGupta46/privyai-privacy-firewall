"""
app/db/models/document.py

Document model — tracks uploaded documents.

Storage:
  The actual file bytes are NOT stored in the database.
  The row records WHERE the file lives (file_path / storage_key), HOW BIG it is
  (size_bytes) and WHERE it is in its lifecycle (status).

Privacy contract:
  Never store extracted text, previews or detected values here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# Lifecycle values for DocumentModel.status
DOC_STATUS_UPLOADED = "uploaded"   # file saved to storage, not yet scanned
DOC_STATUS_SCANNED = "scanned"     # text extracted + privacy scan completed
DOC_STATUS_FAILED = "failed"       # parsing / scanning failed
DOCUMENT_STATUSES = (DOC_STATUS_UPLOADED, DOC_STATUS_SCANNED, DOC_STATUS_FAILED)


class DocumentModel(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Nullable if anonymous uploads are supported.
    # Replace with a required FK once authentication is implemented.
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Display name only — never use sensitive document content as filename.
    filename: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Reference to the file in the storage service (e.g. S3 key, local file name).
    # This is set by the storage adapter.
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)

    # Location of the stored file (e.g. "tmp_uploads/<uuid>.pdf").
    # Nullable only so rows created before this column existed remain valid.
    file_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # Size of the uploaded file in bytes.
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # uploaded | scanned | failed  (see DOC_STATUS_* above)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=DOC_STATUS_UPLOADED,
        server_default=DOC_STATUS_UPLOADED,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=True
    )

    def to_dict(self) -> dict:
        """Serialise the stored metadata for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "filename": self.filename,
            "storage_key": self.storage_key,
            "file_path": self.file_path,
            "size_bytes": self.size_bytes,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return (
            f"<DocumentModel id={self.id} filename={self.filename!r} "
            f"status={self.status!r}>"
        )
