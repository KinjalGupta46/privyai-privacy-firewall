"""
app/api/routes/health.py

GET /health — liveness + readiness probe.

Returns:
  - Application name and version.
  - Current timestamp.
  - Database reachability (without exposing credentials or internals).
  - LLM provider mode (without exposing API keys).

This endpoint deliberately avoids returning any secrets or internal paths.
"""

from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Return service liveness and basic readiness information."""

    db_status = _check_database()
    llm_info = _llm_info()

    return {
        "status": "ok",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": int(time.time()),
        "database": db_status,
        "llm_provider": llm_info,
    }


def _check_database() -> dict:
    """
    Try to import and ping the database session.
    Returns a safe status dict — never the connection URL or credentials.
    """
    if not settings.DATABASE_URL:
        return {"status": "not_configured", "detail": "DATABASE_URL is not set."}

    try:
        # Import lazily so the app still starts if SQLAlchemy is not installed yet.
        from app.db.session import engine
        from sqlalchemy import text

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "connected"}
    except ImportError:
        return {"status": "unavailable", "detail": "Database module not installed."}
    except Exception as exc:
        # Do NOT include the raw exception message as it may contain the URL.
        return {"status": "error", "detail": "Could not reach the database."}


def _llm_info() -> dict:
    """Return safe LLM configuration info — never the API key."""
    provider = settings.LLM_PROVIDER.lower()
    if provider == "mock":
        return {"provider": "mock", "note": "Mock mode — no real LLM calls."}
    if provider == "openai":
        configured = bool(settings.OPENAI_API_KEY)
        return {"provider": "openai", "model": settings.OPENAI_MODEL, "key_set": configured}
    if provider == "gemini":
        configured = bool(settings.GEMINI_API_KEY)
        return {"provider": "gemini", "model": settings.GEMINI_MODEL, "key_set": configured}
    if provider == "anthropic":
        configured = bool(settings.ANTHROPIC_API_KEY)
        return {"provider": "anthropic", "model": settings.ANTHROPIC_MODEL, "key_set": configured}
    return {"provider": provider, "note": "Unknown provider."}
