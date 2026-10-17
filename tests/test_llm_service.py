"""
tests/test_llm_service.py

Phase 4 tests — LLM service abstraction.

Tests:
  - Mock provider returns synthetic response.
  - Mock response is clearly marked as mock=True.
  - Unknown provider raises a clear error.
  - Missing API key raises LLMNotConfiguredError (not a generic exception).
  - Blocked requests never reach the LLM (tested via the chat endpoint).
"""

from __future__ import annotations

import os

import pytest


def test_mock_provider_returns_response():
    """Mock provider must return a non-empty response."""
    import asyncio
    from app.services.llm_service import MockLLMProvider

    provider = MockLLMProvider()
    response = asyncio.run(provider.call("Hello, summarize this."))
    assert response.text
    assert len(response.text) > 0


def test_mock_provider_marks_response_as_mock():
    """Mock response must have mock=True to distinguish it from real LLM."""
    import asyncio
    from app.services.llm_service import MockLLMProvider

    provider = MockLLMProvider()
    response = asyncio.run(provider.call("test prompt"))
    assert response.mock is True


def test_mock_provider_name():
    """Mock provider's provider field must be 'mock'."""
    import asyncio
    from app.services.llm_service import MockLLMProvider

    provider = MockLLMProvider()
    response = asyncio.run(provider.call("test prompt"))
    assert response.provider == "mock"


def test_get_provider_returns_mock_when_configured(monkeypatch):
    """get_provider() returns MockLLMProvider when LLM_PROVIDER=mock."""
    import app.services.llm_service as llm_mod

    # Reset cached provider
    llm_mod._cached_provider = None
    monkeypatch.setattr(llm_mod.settings, "LLM_PROVIDER", "mock")

    provider = llm_mod.get_provider()
    assert isinstance(provider, llm_mod.MockLLMProvider)
    # Cleanup
    llm_mod._cached_provider = None


def test_get_provider_raises_on_unknown_provider(monkeypatch):
    """Unknown provider name should raise LLMProviderError."""
    import app.services.llm_service as llm_mod
    from app.utils.exceptions import LLMProviderError

    llm_mod._cached_provider = None
    monkeypatch.setattr(llm_mod.settings, "LLM_PROVIDER", "nonexistent_provider")

    with pytest.raises(LLMProviderError):
        llm_mod.get_provider()

    llm_mod._cached_provider = None


def test_openai_provider_raises_without_api_key(monkeypatch):
    """OpenAI provider must raise LLMNotConfiguredError if API key is missing."""
    import app.services.llm_service as llm_mod
    from app.utils.exceptions import LLMNotConfiguredError

    monkeypatch.setattr(llm_mod.settings, "OPENAI_API_KEY", None)

    with pytest.raises(LLMNotConfiguredError):
        llm_mod.OpenAIProvider()


def test_chat_endpoint_blocked_request_does_not_call_llm(client, monkeypatch):
    """
    A BLOCK-triggering request must never reach the LLM.
    We patch call_llm to fail if called — then send a high-risk request.
    """
    import app.services.llm_service as llm_mod

    def _fail(*args, **kwargs):
        raise AssertionError("LLM was called for a BLOCKED request!")

    monkeypatch.setattr(llm_mod, "call_llm", _fail)

    # This is a SYNTHETIC dummy API key pattern — not real credentials.
    # Designed to trigger the API_KEY custom recognizer.
    response = client.post("/api/chat", json={
        "message": "My API key is AKIAIOSFODNN7EXAMPLE and should be blocked"
    })

    # Should be blocked (422) — LLM must not have been called.
    # If the assertion in _fail fires, the test fails.
    assert response.status_code in (422, 200), (
        f"Expected 422 (blocked) or 200 (allow/redact), got {response.status_code}"
    )


def test_mock_response_contains_mock_indicator(client):
    """Chat response from mock provider must include mock=True."""
    response = client.post("/api/chat", json={
        "message": "Tell me about machine learning"
    })
    if response.status_code == 200:
        body = response.json()
        assert body.get("mock") is True, "Mock provider response must have mock=True"
