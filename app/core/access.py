"""
app/core/access.py

Access control and user identification dependencies.
"""
from __future__ import annotations

from typing import Optional


def get_current_user_id() -> Optional[int]:
    """
    Return the authenticated user ID, or None in open/anonymous mode.
    """
    return None
