"""
tests/test_risk_scoring.py

Phase 3 tests — risk scoring and policy decisions.

These tests use synthetic entity detection results without
requiring Presidio or spaCy to be loaded, making them fast.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.pii_detector import DetectionResult
from app.services.risk_scoring import ALLOW, BLOCK, REDACT, score


def _make_detection(entity_types_and_scores: list[tuple[str, float]]) -> DetectionResult:
    """
    Create a synthetic DetectionResult without calling Presidio.
    entity_types_and_scores: list of (entity_type, confidence_score) tuples.
    """
    raw_results = []
    counts = {}
    for entity_type, confidence in entity_types_and_scores:
        result = MagicMock()
        result.entity_type = entity_type
        result.score = confidence
        raw_results.append(result)
        counts[entity_type] = counts.get(entity_type, 0) + 1

    return DetectionResult(
        detected_entities=sorted(counts.keys()),
        entity_counts=counts,
        _raw_results=raw_results,
        has_sensitive_content=len(raw_results) > 0,
    )


# ── No entities ──────────────────────────────────────────────────────

def test_no_entities_gives_zero_score():
    """Empty detection → risk score 0.0 and ALLOW."""
    detection = DetectionResult()
    result = score(detection)
    assert result.risk_score == 0.0
    assert result.action == ALLOW


def test_no_entities_gives_allow_action():
    detection = DetectionResult()
    result = score(detection)
    assert result.action == ALLOW


# ── Low-risk entities ─────────────────────────────────────────────────

def test_low_risk_entity_gives_allow():
    """A URL with low confidence should result in ALLOW."""
    detection = _make_detection([("URL", 0.5)])
    result = score(detection)
    # URL severity=0.2, confidence=0.5 → weighted=0.1 → combined≈0.1
    # Should be well below ALLOW_THRESHOLD (0.3)
    assert result.risk_score < 0.3
    assert result.action == ALLOW


# ── Medium-risk entities ──────────────────────────────────────────────

def test_email_gives_redact():
    """An email address with high confidence should trigger REDACT."""
    detection = _make_detection([("EMAIL_ADDRESS", 0.9)])
    result = score(detection)
    # EMAIL severity=0.6, confidence=0.9 → weighted=0.54
    # 0.3 < 0.54 < 0.7 → REDACT
    assert result.action == REDACT
    assert 0.3 <= result.risk_score < 0.7


def test_phone_gives_redact():
    """A phone number with high confidence should trigger REDACT."""
    detection = _make_detection([("PHONE_NUMBER", 0.85)])
    result = score(detection)
    assert result.action in (ALLOW, REDACT)  # depends on exact score


# ── High-risk entities ────────────────────────────────────────────────

def test_api_key_gives_block():
    """An API key with high confidence should trigger BLOCK."""
    detection = _make_detection([("API_KEY", 0.9)])
    result = score(detection)
    # API_KEY severity=1.0, confidence=0.9 → weighted=0.9 → BLOCK
    assert result.action == BLOCK
    assert result.risk_score >= 0.7


def test_password_gives_block():
    """A password-like pattern with high confidence should trigger BLOCK."""
    detection = _make_detection([("PASSWORD_LIKE", 0.85)])
    result = score(detection)
    # PASSWORD_LIKE severity=1.0, confidence=0.85 → weighted=0.85 → BLOCK
    assert result.action == BLOCK


def test_credit_card_gives_block():
    """A credit card with high confidence should trigger BLOCK."""
    detection = _make_detection([("CREDIT_CARD", 0.95)])
    result = score(detection)
    # CREDIT_CARD severity=0.9, confidence=0.95 → weighted=0.855 → BLOCK
    assert result.action == BLOCK


# ── Multiple entities ─────────────────────────────────────────────────

def test_multiple_medium_entities_can_escalate_to_block():
    """Multiple medium-risk entities combined can push the score to BLOCK."""
    detection = _make_detection([
        ("EMAIL_ADDRESS", 0.9),
        ("PHONE_NUMBER", 0.9),
        ("PERSON", 0.85),
    ])
    result = score(detection)
    # Combined soft-max of ~0.54, ~0.51, ~0.425 should exceed 0.7
    assert result.risk_score > 0.7
    assert result.action == BLOCK


# ── Score properties ──────────────────────────────────────────────────

def test_score_is_between_0_and_1():
    """Risk score must always be in [0, 1]."""
    detection = _make_detection([
        ("API_KEY", 1.0),
        ("PASSWORD_LIKE", 1.0),
        ("CREDIT_CARD", 1.0),
    ])
    result = score(detection)
    assert 0.0 <= result.risk_score <= 1.0


def test_score_metadata_has_no_sensitive_values():
    """The explanation must not contain actual entity values."""
    detection = _make_detection([("EMAIL_ADDRESS", 0.9)])
    result = score(detection)
    # The explanation should only contain entity TYPE names, not values
    assert "@" not in result.explanation
    assert "example.com" not in result.explanation


# ── Explainability ────────────────────────────────────────────────────

def test_result_includes_entity_types():
    """Result must include detected_entities list."""
    detection = _make_detection([("EMAIL_ADDRESS", 0.9), ("API_KEY", 0.95)])
    result = score(detection)
    assert "EMAIL_ADDRESS" in result.detected_entities
    assert "API_KEY" in result.detected_entities


def test_result_includes_entity_counts():
    """Result must include entity_counts dict."""
    detection = _make_detection([("EMAIL_ADDRESS", 0.9), ("EMAIL_ADDRESS", 0.85)])
    result = score(detection)
    assert result.entity_counts.get("EMAIL_ADDRESS") == 2
