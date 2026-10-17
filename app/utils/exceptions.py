"""
app/utils/exceptions.py

Custom exception classes and a FastAPI exception handler factory.
Keeps error responses consistent across all endpoints and avoids
leaking stack traces or sensitive values to API consumers.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class PrivyAIError(Exception):
    """Base class for all PrivyAI-specific errors."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ValidationError(PrivyAIError):
    """Raised when request input fails validation (400)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=400)


class FileTooLargeError(PrivyAIError):
    """Raised when an uploaded file exceeds the size limit (413)."""

    def __init__(self, max_mb: int) -> None:
        super().__init__(
            f"File exceeds the maximum allowed size of {max_mb} MB.",
            status_code=413,
        )


class UnsupportedFileTypeError(PrivyAIError):
    """Raised when an uploaded file has an unsupported MIME type (415)."""

    def __init__(self, content_type: str) -> None:
        super().__init__(
            f"File type '{content_type}' is not supported. "
            "Upload a PDF or DOCX document.",
            status_code=415,
        )


class RequestBlockedError(PrivyAIError):
    """Raised when the privacy policy blocks a request (422)."""

    def __init__(self, reason: str = "Request blocked by privacy policy.") -> None:
        super().__init__(reason, status_code=422)


class LLMProviderError(PrivyAIError):
    """Raised when the LLM provider call fails (502)."""

    def __init__(self, detail: str = "LLM provider error.") -> None:
        super().__init__(detail, status_code=502)


class LLMNotConfiguredError(PrivyAIError):
    """Raised when no LLM provider is configured and mock mode is off (503)."""

    def __init__(self) -> None:
        super().__init__(
            "No LLM provider is configured. "
            "Set LLM_PROVIDER=mock in .env for local development, "
            "or supply a valid provider and API key.",
            status_code=503,
        )


class DatabaseError(PrivyAIError):
    """Raised when a database operation fails (503)."""

    def __init__(self, detail: str = "Database operation failed.") -> None:
        super().__init__(detail, status_code=503)


# ------------------------------------------------------------------ #
# FastAPI exception handler registration                               #
# ------------------------------------------------------------------ #

def register_exception_handlers(app: FastAPI) -> None:
    """Attach all custom exception handlers to a FastAPI app instance."""

    @app.exception_handler(PrivyAIError)
    async def privy_error_handler(request: Request, exc: PrivyAIError) -> JSONResponse:
        # Never include internal details (stack traces, sensitive values).
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message, "status_code": exc.status_code},
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        # Catch-all to prevent accidental leakage of stack traces in production.
        return JSONResponse(
            status_code=500,
            content={"error": "An internal server error occurred.", "status_code": 500},
        )
