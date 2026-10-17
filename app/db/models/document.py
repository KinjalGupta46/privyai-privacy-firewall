"""
app/db/models/document.py

Document model — tracks uploaded documents.

Storage:
  The actual file bytes are NOT stored in MySQL.
  Only a reference (storage_key) to the file in the storage service is kept.
  Your file-storage teammate should provide the actual storage implementation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


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

    # Reference to the file in the storage service (e.g. S3 key, local path).
    # This is set by the storage adapter.
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<DocumentModel id={self.id} filename={self.filename!r}>"
