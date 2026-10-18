"""
app/db/session.py

SQLAlchemy engine and session factory.

Usage:
    from app.db.session import get_db_session

    with get_db_session() as session:
        session.add(my_model)
        session.commit()

The session is automatically closed when the context manager exits,
even if an exception is raised.

Database configuration:
  Set DATABASE_URL in .env:
    postgresql+psycopg://user:password@localhost:5432/privyai_db

  If DATABASE_URL is not set, all DB operations will raise an error.
  The application will still start — scan history just won't be persisted.

Schema creation (development only):
  Do NOT use Base.metadata.create_all() in production.
  For local development, run:
    python -c "from app.db.session import create_tables; create_tables()"

  For production, use Alembic migrations (see README).
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.utils.exceptions import DatabaseError

logger = logging.getLogger(__name__)

# Engine is created lazily on first use.
_engine = None
_SessionLocal = None


def _get_engine():
    """Return the SQLAlchemy engine, creating it on first call."""
    global _engine, _SessionLocal
    if _engine is None:
        if not settings.DATABASE_URL:
            raise DatabaseError(
                "DATABASE_URL is not configured. "
                "Set it in .env to enable scan history."
            )
        if settings.DATABASE_URL.startswith("sqlite"):
            _engine = create_engine(
                settings.DATABASE_URL,
                connect_args={"check_same_thread": False},
            )
        else:
            _engine = create_engine(
                settings.DATABASE_URL,
                # Connection pool settings suitable for a small backend.
                pool_pre_ping=True,      # Detect stale connections.
                pool_recycle=3600,       # Recycle connections after 1 hour.
                pool_size=5,
                max_overflow=10,
                echo=False,              # Set True for SQL debug logging.
            )
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=_engine,
        )
    return _engine


# Public alias so health.py can import it for connectivity checks.
@property
def engine():
    return _get_engine()


# Make it importable as `from app.db.session import engine`
class _EngineProxy:
    """Proxy that creates the engine on first attribute access."""
    def __getattr__(self, name):
        return getattr(_get_engine(), name)

    def connect(self):
        return _get_engine().connect()


engine = _EngineProxy()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager that yields an SQLAlchemy Session.

    Automatically commits on success and rolls back on error.
    Always closes the session when the context manager exits.

    Example:
        with get_db_session() as session:
            session.add(scan)
            session.commit()
    """
    eng = _get_engine()
    session: Session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_tables() -> None:
    """
    Create all tables defined by ORM models (development use only).

    In production, use Alembic migrations instead of this function.
    See README.md for the full migration workflow.

    Run with:
        python -c "from app.db.session import create_tables; create_tables()"
    """
    from app.db.base import Base
    import app.db.models.user  # noqa: F401
    import app.db.models.document  # noqa: F401
    import app.db.models.privacy_scan  # noqa: F401
    import app.db.models.detected_entity  # noqa: F401
    import app.db.models.audit_log  # noqa: F401

    eng = _get_engine()
    logger.warning(
        "Creating database tables (DEVELOPMENT ONLY). "
        "Use Alembic in production."
    )
    Base.metadata.create_all(bind=eng)
    logger.info("Tables created successfully.")
