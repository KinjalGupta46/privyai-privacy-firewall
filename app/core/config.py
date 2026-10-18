"""
app/core/config.py

Centralized configuration for PrivyAI backend.
All values are read from environment variables (or a .env file).
Never hard-code secrets here.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings loaded from environment variables.

    Add a new variable here to expose it to the rest of the application.
    The name of the attribute becomes the environment-variable name (case-insensitive).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # unknown env vars are silently ignored
    )

    # ------------------------------------------------------------------ #
    # Application metadata                                                 #
    # ------------------------------------------------------------------ #
    APP_NAME: str = "PrivyAI Backend"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # ------------------------------------------------------------------ #
    # Server                                                               #
    # ------------------------------------------------------------------ #
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ------------------------------------------------------------------ #
    # CORS – comma-separated list of allowed origins.                      #
    # Example: ALLOWED_ORIGINS=http://localhost:3000,https://myapp.com     #
    # Default is restrictive (localhost only) for safety.                  #
    # ------------------------------------------------------------------ #
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def allowed_origins_list(self) -> List[str]:
        """Return ALLOWED_ORIGINS parsed into a Python list."""
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

       # ------------------------------------------------------------------ #
    # Database (PostgreSQL via SQLAlchemy)                                #
    # Leave blank to run without a database (scan history disabled).     #
    # ------------------------------------------------------------------ #
    DATABASE_URL: Optional[str] = Field(
        default=None,
        description=(
            "SQLAlchemy PostgreSQL connection URL. "
            "Example: postgresql+psycopg://user:password@localhost:5432/privyai_db"
        ),
    )

    # ------------------------------------------------------------------ #
    # LLM provider                                                         #
    # ------------------------------------------------------------------ #
    # Set LLM_PROVIDER to one of: "mock", "openai", "gemini", "anthropic"
    # If you have not decided on a provider yet, keep it as "mock".
    LLM_PROVIDER: str = "mock"

    # Provider-specific API keys – leave empty if not using that provider.
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: Optional[str] = None  # optional custom endpoint

    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"

    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-haiku-4-5"

    # Timeout for LLM API calls (seconds)
    LLM_TIMEOUT: int = 30

    # Max tokens in the LLM reply, and automatic retries on 429 / 5xx errors.
    LLM_MAX_TOKENS: int = 1024
    LLM_MAX_RETRIES: int = 2

    # ------------------------------------------------------------------ #
    # Privacy pipeline thresholds                                          #
    # ------------------------------------------------------------------ #
    # Presidio detection confidence threshold (0.0–1.0).
    # Entities with confidence below this value are ignored.
    PII_CONFIDENCE_THRESHOLD: float = 0.5

    # Risk score thresholds for policy decisions.
    # Score below ALLOW_THRESHOLD  → ALLOW (no sensitive content)
    # Score below REDACT_THRESHOLD → REDACT (mask and forward)
    # Score >= REDACT_THRESHOLD    → BLOCK  (do not forward to LLM)
    RISK_ALLOW_THRESHOLD: float = 0.3
    RISK_REDACT_THRESHOLD: float = 0.7

    # ------------------------------------------------------------------ #
    # File upload limits                                                   #
    # ------------------------------------------------------------------ #
    MAX_UPLOAD_SIZE_MB: int = 10  # maximum document upload size in MB
    MAX_MESSAGE_LENGTH: int = 10_000  # max characters in a chat message

    # ------------------------------------------------------------------ #
    # Storage adapter                                                      #
    # ------------------------------------------------------------------ #
    # "local" uses a temp directory (development only, not production-safe).
    # Replace with your team's storage adapter when available.
    STORAGE_ADAPTER: str = "local"
    LOCAL_STORAGE_PATH: str = "tmp_uploads"  # relative to project root

    @field_validator("PII_CONFIDENCE_THRESHOLD", "RISK_ALLOW_THRESHOLD", "RISK_REDACT_THRESHOLD")
    @classmethod
    def _validate_float_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("Threshold must be between 0.0 and 1.0")
        return v

    @field_validator("RISK_REDACT_THRESHOLD")
    @classmethod
    def _redact_above_allow(cls, v: float) -> float:
        # We cannot easily compare against RISK_ALLOW_THRESHOLD here because
        # pydantic validators run field-by-field.  We validate the ordering
        # at application startup in main.py instead.
        return v


# Singleton – import and use `settings` everywhere in the application.
settings = Settings()
