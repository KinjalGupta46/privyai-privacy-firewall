"""
tests/conftest.py

Shared pytest fixtures for all PrivyAI backend tests.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


# ── Environment overrides for tests ──────────────────────────────────────────
# Set these before importing app so that pydantic-settings picks them up.
# We always use mock LLM and skip the database in unit tests.
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("DATABASE_URL", "")   # disable DB for unit tests
os.environ.setdefault("DEBUG", "true")


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Return a FastAPI TestClient that persists across the test session."""
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)
