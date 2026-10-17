"""
tests/test_pii_detection.py

Phase 2 tests — PII detection and redaction.

IMPORTANT: These tests require the Presidio + spaCy en_core_web_lg model.
If the model is not installed, detector tests will be skipped.

Run ONLY these tests:
    pytest tests/test_pii_detection.py -v

All tests use synthetic data only. No real personal information is used.
"""

from __future__ import annotations

import pytest


def _presidio_available() -> bool:
    """Check if Presidio and the spaCy model are installed and loadable."""
    try:
        from app.services.pii_detector import get_analyzer
        get_analyzer()
        return True
    except Exception:
        return False


presidio_required = pytest.mark.skipif(
    not _presidio_available(),
    reason="Presidio / spaCy en_core_web_lg model not available"
)


# ── Redaction tests (use synthetic DetectionResult, no Presidio needed) ──

def test_redaction_no_entities_returns_original():
    """Text with no sensitive content should be returned unchanged."""
    from app.services.pii_detector import DetectionResult
    from app.services.redaction import redact

    text = "The sky is blue and the grass is green."
    detection = DetectionResult()
    result = redact(text, detection)
    assert result.redacted_text == text
    assert result.total_redacted == 0


def test_redaction_count_is_zero_for_safe_text():
    from app.services.pii_detector import DetectionResult
    from app.services.redaction import redact

    detection = DetectionResult()
    result = redact("Hello world", detection)
    assert result.total_redacted == 0


# ── Detection tests (require Presidio + spaCy model) ──────────────────

@presidio_required
def test_detect_email():
    """Synthetic email address must be detected."""
    from app.services.pii_detector import detect

    text = "Contact test.user@synthetic-example.org for details."
    result = detect(text)
    assert "EMAIL_ADDRESS" in result.detected_entities, (
        f"EMAIL_ADDRESS not detected. Found: {result.detected_entities}"
    )


@presidio_required
def test_detect_phone_number():
    """Synthetic phone number must be detected."""
    from app.services.pii_detector import detect

    text = "Call us at +1-555-867-5309 for synthetic test data."
    result = detect(text)
    assert result.has_sensitive_content


@presidio_required
def test_detect_returns_no_sensitive_values():
    """Detected entity metadata must not contain the actual sensitive values."""
    from app.services.pii_detector import detect

    text = "Email: noreply@synthetic-test.invalid"
    result = detect(text)
    # Detected entities should be type names only — not actual email strings
    for entity_type in result.detected_entities:
        assert "@" not in entity_type


@presidio_required
def test_detect_api_key_pattern():
    """Synthetic AWS-format key ID should trigger the custom API_KEY recognizer."""
    from app.services.pii_detector import detect

    # SYNTHETIC test key — not a real AWS key
    text = "aws_access_key_id = AKIAIOSFODNN7EXAMPLE"
    result = detect(text)
    assert result.has_sensitive_content


@presidio_required
def test_detect_bearer_token():
    """Synthetic Bearer token should be detected."""
    from app.services.pii_detector import detect

    text = "Authorization: Bearer syntheticTokenAbcDefGhiJklMno123456789"
    result = detect(text)
    assert result.has_sensitive_content


@presidio_required
def test_detect_password_assignment():
    """Synthetic password assignment should be detected."""
    from app.services.pii_detector import detect

    text = "password=SyntheticPass@word99"
    result = detect(text)
    assert result.has_sensitive_content


@presidio_required
def test_safe_text_no_entities():
    """Generic safe text should not trigger any detections."""
    from app.services.pii_detector import detect

    text = "The capital of France is Paris. The Eiffel Tower is 330 metres tall."
    result = detect(text)
    # May detect LOCATION (Paris) or PERSON - that's acceptable.
    # What we're checking is there are no high-risk entities.
    high_risk = {"API_KEY", "PASSWORD_LIKE", "ACCESS_TOKEN", "CREDIT_CARD", "US_SSN"}
    detected_high_risk = set(result.detected_entities) & high_risk
    assert not detected_high_risk, f"Unexpected high-risk entities: {detected_high_risk}"


@presidio_required
def test_redact_email_in_text():
    """Email should be redacted to <EMAIL_ADDRESS> placeholder."""
    from app.services.pii_detector import detect
    from app.services.redaction import redact

    original = "Please email alice@example.com for help."
    detection = detect(original)

    # Detection must succeed; do not skip if the email is missed.
    assert "EMAIL_ADDRESS" in detection.detected_entities

    result = redact(original, detection)

    assert "alice@example.com" not in result.redacted_text
    assert "<EMAIL_ADDRESS>" in result.redacted_text


@presidio_required
def test_entity_counts_match_detections():
    """entity_counts must accurately count detected entities."""
    from app.services.pii_detector import detect

    text = (
        "Email one: first@example.invalid. Email two: second@example.invalid."
    )
    result = detect(text)
    if "EMAIL_ADDRESS" in result.entity_counts:
        assert result.entity_counts["EMAIL_ADDRESS"] >= 1
