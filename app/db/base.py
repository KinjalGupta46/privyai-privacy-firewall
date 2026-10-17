"""
app/db/base.py

SQLAlchemy declarative base for all ORM models.

All models in app/db/models/ must inherit from Base.
This ensures they are registered with SQLAlchemy's metadata
and can be created/migrated as a group.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass
