"""
tests/test_chat_endpoint.py

Phase 4 tests — /api/chat endpoint (integration tests using mock LLM).

These tests use the mock LLM provider (no real API key needed).
PII detection tests that require spaCy are marked with @pytest.mark.spacy
and can be skipped if the model is not installed.
"""

from __future__ import annotations

import pytest


# ── Basic endpoint tests ──────────────────────────────────────────────

def test_chat_endpoint_exists(client):
    """POST /api/chat must exist (not 404)."""
    response = client.post("/api/chat", json={"message": "Hello"})
    assert response.status_code != 404


def test_chat_with_safe_message_returns_200(client):
    """A message with no sensitive content should return 200."""
    response = client.post("/api/chat", json={"message": "Tell me about the weather"})
    assert response.status_code == 200


def test_chat_response_structure(client):
    """Response must include all required fields."""
    response = client.post("/api/chat", json={"message": "Hello world"})
    if response.status_code == 200:
        body = response.json()
        required = {"response", "action", "detected_entities", "entity_counts",
                    "risk_score", "output_action", "request_id", "mock"}
        missing = required - body.keys()
        assert not missing, f"Missing response fields: {missing}"


def test_chat_response_action_is_valid(client):
    """action field must be one of ALLOW, REDACT, BLOCK."""
    response = client.post("/api/chat", json={"message": "Summarize this document"})
    if response.status_code == 200:
        body = response.json()
        assert body["action"] in ("ALLOW", "REDACT", "BLOCK")


def test_chat_risk_score_in_range(client):
    """risk_score must be between 0.0 and 1.0."""
    response = client.post("/api/chat", json={"message": "Hello there"})
    if response.status_code == 200:
        body = response.json()
        assert 0.0 <= body["risk_score"] <= 1.0


def test_chat_request_id_is_uuid(client):
    """request_id must be a UUID-like string."""
    import re
    response = client.post("/api/chat", json={"message": "Hello"})
    if response.status_code == 200:
        body = response.json()
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        assert re.match(uuid_pattern, body["request_id"], re.IGNORECASE)


def test_chat_unique_request_ids(client):
    """Each request must have a unique request_id."""
    ids = set()
    for _ in range(5):
        r = client.post("/api/chat", json={"message": "Hello"})
        if r.status_code == 200:
            ids.add(r.json()["request_id"])
    assert len(ids) == 5


# ── Input validation ──────────────────────────────────────────────────

def test_chat_empty_message_returns_error(client):
    """Empty message must return a 422 validation error."""
    response = client.post("/api/chat", json={"message": ""})
    assert response.status_code == 422


def test_chat_missing_message_returns_error(client):
    """Missing message field must return a 422 validation error."""
    response = client.post("/api/chat", json={})
    assert response.status_code == 422


def test_chat_overly_long_message_returns_error(client):
    """Message exceeding MAX_MESSAGE_LENGTH must be rejected."""
    from app.core.config import settings
    long_msg = "a" * (settings.MAX_MESSAGE_LENGTH + 1)
    response = client.post("/api/chat", json={"message": long_msg})
    assert response.status_code == 422


# ── Mock LLM ──────────────────────────────────────────────────────────

def test_chat_mock_provider_response_has_mock_true(client):
    """Mock provider must set mock=True in the response."""
    response = client.post("/api/chat", json={"message": "Tell me something"})
    if response.status_code == 200:
        assert response.json().get("mock") is True


def test_chat_response_not_empty(client):
    """Response text must not be empty."""
    response = client.post("/api/chat", json={"message": "Explain Python"})
    if response.status_code == 200:
        body = response.json()
        assert body["response"]
        assert len(body["response"]) > 0


# ── Output scanning ───────────────────────────────────────────────────

def test_output_action_is_valid(client):
    """output_action must be ALLOW, REDACT, or BLOCK."""
    response = client.post("/api/chat", json={"message": "Hello world"})
    if response.status_code == 200:
        body = response.json()
        assert body["output_action"] in ("ALLOW", "REDACT", "BLOCK")


# ── No secrets in response ────────────────────────────────────────────

def test_chat_response_does_not_leak_api_keys(client):
    """Response metadata must not contain any API key or password values."""
    # Synthetic dummy key — not a real credential
    response = client.post("/api/chat", json={
        "message": "My config has password=SuperSecret123"
    })
    raw = response.text
    # The original values should NOT appear anywhere in the response
    assert "SuperSecret123" not in raw, "Original secret value leaked in response"
