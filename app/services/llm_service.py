"""
app/services/llm_service.py

LLM provider abstraction layer.

Design principles:
  - The application never sends the original (unredacted) input to the LLM.
    Only the sanitised, redacted text is passed to this service.
  - Credentials come from environment variables — never hard-coded.
  - Provider is configurable; the interface is the same for all providers.
  - When LLM_PROVIDER=mock, a clearly-labelled synthetic response is returned.
    Mock responses are distinguishable from real LLM responses via the
    'mock' field in the return value.
  - If a real provider is configured but the API key is missing, a clear
    LLMNotConfiguredError is raised — we never silently fall back to mock.

To add a new provider:
  1. Add a new class inheriting from BaseLLMProvider.
  2. Implement the call() method.
  3. Add it to _PROVIDERS in get_provider().

IMPORTANT: Do not log the prompt or completion — they may contain
           redacted placeholders but could still carry partial context.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.config import settings
from app.utils.exceptions import LLMNotConfiguredError, LLMProviderError

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────
# Response dataclass
# ────────────────────────────────────────────────────────────────────

@dataclass
class LLMResponse:
    """Structured response from any LLM provider."""
    text: str           # The generated text (may still need output scanning)
    provider: str       # "mock" | "openai" | "gemini" | "anthropic"
    model: str          # Model identifier
    mock: bool = False  # True → response is synthetic, not from a real LLM


# ────────────────────────────────────────────────────────────────────
# Provider interface
# ────────────────────────────────────────────────────────────────────

class BaseLLMProvider(ABC):
    """Abstract base class all LLM providers must implement."""

    @abstractmethod
    async def call(self, prompt: str) -> LLMResponse:
        """
        Send *prompt* to the LLM and return the response.

        The prompt MUST already be redacted before this method is called.
        This method must never receive the original unredacted text.
        """
        ...


# ────────────────────────────────────────────────────────────────────
# Mock provider (development / testing)
# ────────────────────────────────────────────────────────────────────

class MockLLMProvider(BaseLLMProvider):
    """
    Returns a clearly-labelled synthetic response.

    Use for local development, CI tests, and demos without a real API key.
    NEVER use this in production when real answers are expected.
    """

    async def call(self, prompt: str) -> LLMResponse:
        # We intentionally do not log the prompt.
        return LLMResponse(
            text=(
                "[MOCK RESPONSE] This is a synthetic response from the PrivyAI mock "
                "LLM provider. Set LLM_PROVIDER to 'openai', 'gemini', or 'anthropic' "
                "and supply the corresponding API key to use a real language model."
            ),
            provider="mock",
            model="mock-v1",
            mock=True,
        )


# ────────────────────────────────────────────────────────────────────
# OpenAI provider
# ────────────────────────────────────────────────────────────────────

class OpenAIProvider(BaseLLMProvider):
    """OpenAI ChatCompletion provider (requires openai package)."""

    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY:
            raise LLMNotConfiguredError()
        try:
            import openai  # noqa: F401 — checked at init
        except ImportError:
            raise LLMProviderError(
                "The 'openai' package is not installed. "
                "Run: pip install openai==1.57.0"
            )
        self._api_key = settings.OPENAI_API_KEY
        self._model = settings.OPENAI_MODEL
        self._base_url = settings.OPENAI_BASE_URL

    async def call(self, prompt: str) -> LLMResponse:
        import openai

        client = openai.AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url or None,
        )
        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=self._model,
                    messages=[{"role": "user", "content": prompt}],
                ),
                timeout=settings.LLM_TIMEOUT,
            )
            text = response.choices[0].message.content or ""
            return LLMResponse(text=text, provider="openai", model=self._model)
        except asyncio.TimeoutError:
            raise LLMProviderError("OpenAI API call timed out.")
        except Exception as exc:
            # Never include the exception string in the API response as
            # it may contain request details.
            logger.error("OpenAI API error (details omitted from response): %s", type(exc).__name__)
            raise LLMProviderError("OpenAI API call failed.")


# ────────────────────────────────────────────────────────────────────
# Gemini provider
# ────────────────────────────────────────────────────────────────────

class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider (requires google-generativeai package)."""

    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise LLMNotConfiguredError()
        try:
            import google.generativeai as genai  # noqa: F401
        except ImportError:
            raise LLMProviderError(
                "The 'google-generativeai' package is not installed. "
                "Run: pip install google-generativeai==0.8.3"
            )
        self._api_key = settings.GEMINI_API_KEY
        self._model = settings.GEMINI_MODEL

    async def call(self, prompt: str) -> LLMResponse:
        import google.generativeai as genai

        genai.configure(api_key=self._api_key)
        model = genai.GenerativeModel(self._model)

        try:
            # Gemini's Python SDK uses sync calls — run in executor to
            # avoid blocking the event loop.
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(None, model.generate_content, prompt),
                timeout=settings.LLM_TIMEOUT,
            )
            text = response.text or ""
            return LLMResponse(text=text, provider="gemini", model=self._model)
        except asyncio.TimeoutError:
            raise LLMProviderError("Gemini API call timed out.")
        except Exception as exc:
            logger.error("Gemini API error (details omitted): %s", type(exc).__name__)
            raise LLMProviderError("Gemini API call failed.")


# ────────────────────────────────────────────────────────────────────
# Anthropic provider
# ────────────────────────────────────────────────────────────────────

class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider (requires anthropic package)."""

    def __init__(self) -> None:
        if not settings.ANTHROPIC_API_KEY:
            raise LLMNotConfiguredError()
        try:
            import anthropic  # noqa: F401
        except ImportError:
            raise LLMProviderError(
                "The 'anthropic' package is not installed. "
                "Run: pip install anthropic==0.40.0"
            )
        self._api_key = settings.ANTHROPIC_API_KEY
        self._model = settings.ANTHROPIC_MODEL

    async def call(self, prompt: str) -> LLMResponse:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self._api_key)
        try:
            response = await asyncio.wait_for(
                client.messages.create(
                    model=self._model,
                    max_tokens=2048,
                    messages=[{"role": "user", "content": prompt}],
                ),
                timeout=settings.LLM_TIMEOUT,
            )
            text = response.content[0].text if response.content else ""
            return LLMResponse(text=text, provider="anthropic", model=self._model)
        except asyncio.TimeoutError:
            raise LLMProviderError("Anthropic API call timed out.")
        except Exception as exc:
            logger.error("Anthropic API error (details omitted): %s", type(exc).__name__)
            raise LLMProviderError("Anthropic API call failed.")


# ────────────────────────────────────────────────────────────────────
# Provider registry and factory
# ────────────────────────────────────────────────────────────────────

_PROVIDER_MAP = {
    "mock": MockLLMProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "anthropic": AnthropicProvider,
}

_cached_provider: BaseLLMProvider | None = None


def get_provider() -> BaseLLMProvider:
    """
    Return the configured LLM provider, creating it on first call.

    The provider is determined by the LLM_PROVIDER environment variable.
    Raises LLMNotConfiguredError if the provider is unknown or not configured.
    """
    global _cached_provider
    if _cached_provider is None:
        provider_name = settings.LLM_PROVIDER.lower()
        klass = _PROVIDER_MAP.get(provider_name)
        if klass is None:
            raise LLMProviderError(
                f"Unknown LLM provider: '{provider_name}'. "
                f"Valid options: {', '.join(_PROVIDER_MAP)}"
            )
        _cached_provider = klass()
    return _cached_provider


async def call_llm(sanitized_prompt: str) -> LLMResponse:
    """
    High-level entry point: call the configured LLM with a sanitized prompt.

    This function must only be called with a redacted (sanitized) prompt.
    Calling it with the original unredacted prompt violates the privacy guarantee.

    Args:
        sanitized_prompt: The redacted prompt text from the redaction service.

    Returns:
        LLMResponse from the configured provider.
    """
    provider = get_provider()
    return await provider.call(sanitized_prompt)
