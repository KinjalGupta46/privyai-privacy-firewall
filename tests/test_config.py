"""
tests/test_config.py

Phase 1 tests — application configuration.

Tests:
  - Settings loads without error.
  - ALLOW threshold is strictly less than REDACT threshold.
  - Confidence threshold is within valid range.
  - allowed_origins_list is a non-empty list.
"""

from __future__ import annotations


def test_settings_loads():
    """Settings must instantiate without raising an error."""
    from app.core.config import settings
    assert settings is not None


def test_allow_threshold_less_than_redact():
    """RISK_ALLOW_THRESHOLD must be strictly less than RISK_REDACT_THRESHOLD."""
    from app.core.config import settings
    assert settings.RISK_ALLOW_THRESHOLD < settings.RISK_REDACT_THRESHOLD, (
        f"RISK_ALLOW_THRESHOLD ({settings.RISK_ALLOW_THRESHOLD}) must be < "
        f"RISK_REDACT_THRESHOLD ({settings.RISK_REDACT_THRESHOLD})"
    )


def test_confidence_threshold_in_range():
    """PII_CONFIDENCE_THRESHOLD must be between 0.0 and 1.0."""
    from app.core.config import settings
    assert 0.0 <= settings.PII_CONFIDENCE_THRESHOLD <= 1.0


def test_allowed_origins_list():
    """allowed_origins_list must return a non-empty list of strings."""
    from app.core.config import settings
    origins = settings.allowed_origins_list
    assert isinstance(origins, list)
    assert len(origins) > 0
    for origin in origins:
        assert isinstance(origin, str)


def test_max_upload_size_positive():
    """MAX_UPLOAD_SIZE_MB must be a positive integer."""
    from app.core.config import settings
    assert settings.MAX_UPLOAD_SIZE_MB > 0


def test_max_message_length_positive():
    """MAX_MESSAGE_LENGTH must be a positive integer."""
    from app.core.config import settings
    assert settings.MAX_MESSAGE_LENGTH > 0
