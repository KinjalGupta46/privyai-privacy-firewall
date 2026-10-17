"""
app/main.py

FastAPI application entry point for PrivyAI backend.

What this file does:
  1. Creates the FastAPI app with metadata.
  2. Configures CORS (allowed origins come from .env — never hard-code them).
  3. Registers all API routers.
  4. Registers custom exception handlers.
  5. Validates critical configuration at startup.

Start the server with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.utils.exceptions import register_exception_handlers

# ------------------------------------------------------------------ #
# Logging configuration                                                 #
# ------------------------------------------------------------------ #
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Lifespan (startup + shutdown)                                         #
# ------------------------------------------------------------------ #
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs at startup (before yield) and shutdown (after yield)."""
    # ── Startup ──────────────────────────────────────────────────────
    allow_t = settings.RISK_ALLOW_THRESHOLD
    redact_t = settings.RISK_REDACT_THRESHOLD

    if allow_t >= redact_t:
        raise ValueError(
            f"RISK_ALLOW_THRESHOLD ({allow_t}) must be less than "
            f"RISK_REDACT_THRESHOLD ({redact_t})."
        )

    logger.info("PrivyAI backend starting up — version %s", settings.APP_VERSION)
    logger.info("LLM provider: %s", settings.LLM_PROVIDER)
    logger.info(
        "Risk thresholds — ALLOW: <%.2f | REDACT: %.2f\u2013%.2f | BLOCK: >=%.2f",
        allow_t, allow_t, redact_t, redact_t,
    )
    if not settings.DATABASE_URL:
        logger.warning(
            "DATABASE_URL is not set. Scan history will not be persisted."
        )
    if settings.LLM_PROVIDER == "mock":
        logger.warning(
            "LLM_PROVIDER=mock \u2014 responses are synthetic. "
            "Set a real provider and API key for production."
        )

    yield  # Application runs here

    # ── Shutdown ─────────────────────────────────────────────────────
    logger.info("PrivyAI backend shutting down.")

# ------------------------------------------------------------------ #
# FastAPI application                                                   #
# ------------------------------------------------------------------ #
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "PrivyAI \u2014 Privacy Firewall for AI. "
        "Detects, scores and redacts sensitive information before forwarding "
        "prompts to an external LLM."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,  # modern replacement for @app.on_event
)

# ------------------------------------------------------------------ #
# CORS middleware                                                        #
# ------------------------------------------------------------------ #
# Allowed origins are read from ALLOWED_ORIGINS in .env.
# Do not use allow_origins=["*"] — that would allow any website to call
# this backend from a browser, which is a security risk.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
)

# ------------------------------------------------------------------ #
# Exception handlers                                                    #
# ------------------------------------------------------------------ #
register_exception_handlers(app)

# ------------------------------------------------------------------ #
# Routers                                                               #
# ------------------------------------------------------------------ #
from app.api.routes import health  # noqa: E402 — imported after app creation
from app.api.routes import chat  # noqa: E402

app.include_router(health.router)
app.include_router(chat.router, prefix="/api")

# Phase 3+ routers — will be added as phases are completed.
# from app.api.routes import documents, scans
# app.include_router(documents.router, prefix="/api")
# app.include_router(scans.router, prefix="/api")

