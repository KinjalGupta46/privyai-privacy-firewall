"""
app/db/models/privacy_scan.py

PrivacyScan model — audit record for each processed request.

Privacy contract:
  NEVER store:
    - Original prompts or messages.
    - Redacted text or LLM completions.
    - Actual detected values (emails, SSNs, API keys, etc.).
    - API keys or passwords.

  ONLY store:
    - Entity type names (e.g. "EMAIL_ADDRESS") — not the values.
    - Entity counts per type.
    - The policy action taken (ALLOW / REDACT / BLOCK).
    - The risk score.
    - The output scan action.
    - A request ID for tracing.
    - Timestamps.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base


class PrivacyScanModel(Base):
    __tablename__ = "privacy_scans"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Nullable: anonymous usage is supported until auth is implemented.
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Nullable: set only for document-derived prompts.
    document_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )

    # Entity type names only — not the actual detected values.
    # Example: ["EMAIL_ADDRESS", "PHONE_NUMBER"]
    detected_entity_types: Mapped[Optional[List[str]]] = mapped_column(
        JSON, nullable=True
    )

    # Counts per entity type.
    # Example: {"EMAIL_ADDRESS": 2, "PHONE_NUMBER": 1}
    entity_counts: Mapped[Optional[Dict[str, int]]] = mapped_column(
        JSON, nullable=True
    )

    # ALLOW | REDACT | BLOCK
    action_taken: Mapped[str] = mapped_column(String(10), nullable=False)

    # Heuristic risk score (0.0–1.0).
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ALLOW | REDACT | BLOCK for the output scan.
    output_action: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # UUID for request tracing.
    request_id: Mapped[Optional[str]] = mapped_column(
        String(36), unique=True, nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<PrivacyScanModel id={self.id} "
            f"action={self.action_taken!r} "
            f"score={self.risk_score}>"
        )
