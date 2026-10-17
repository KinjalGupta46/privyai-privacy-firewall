"""
app/core/security.py

Lightweight security utilities for PrivyAI.
Covers request-id generation and basic input sanitisation helpers.
Authentication is not yet implemented; this is noted as a TODO.

NOTE: User-level authentication (JWT / OAuth) is not yet implemented.
      Scan ownership is therefore not enforced.  This must be addressed
      before exposing this backend to untrusted users.
"""

from __future__ import annotations

import uuid


def generate_request_id() -> str:
    """Return a new random UUID4 string to trace a single request."""
    return str(uuid.uuid4())


def sanitize_filename(filename: str) -> str:
    """Return a filename with path-traversal characters removed.

    We keep only alphanumerics, single dots, dashes and underscores.
    This prevents path-traversal attacks where an attacker uploads a file
    named '../../etc/passwd'.
    """
    import re
    # Replace any character that is NOT alphanumeric, dot, dash, or underscore.
    safe = re.sub(r"[^\w.\-]", "_", filename)
    # Collapse double-dots (path traversal: ../.. becomes __) — keep single dots.
    safe = re.sub(r"\.{2,}", "_", safe)
    # Remove leading dots (hidden files).
    safe = safe.lstrip(".")
    # Remove leading/trailing underscores for cleanliness.
    safe = safe.strip("_")
    return safe or "unnamed_file"
