
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DetectedEntityModel(Base):
    __tablename__ = "detected_entities"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    scan_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("privacy_scans.id"), nullable=True
    )
    entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    entity_count: Mapped[Optional[int]] = mapped_column(
        Integer, default=1
    )
    is_masked: Mapped[Optional[bool]] = mapped_column(
        Boolean, default=False
    )
