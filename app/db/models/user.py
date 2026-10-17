"""
app/db/models/user.py

User model — only needed if authentication is implemented.

NOTE: User-level authentication is NOT yet implemented in this backend.
      This model is provided as a template for future integration.
      Until authentication is implemented, scan ownership is not enforced.
      Do not claim per-user scan history is private without proper auth.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<UserModel id={self.id}>"
