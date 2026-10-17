"""
app/services/pii_detector.py

PII / sensitive-data detection service built on Microsoft Presidio.

What it does:
  1. Runs Presidio's AnalyzerEngine against a text string.
  2. Applies custom regex recognizers for patterns Presidio may miss
     (API keys, bearer tokens, secret-like strings, passwords).
  3. Filters detections by a configurable confidence threshold.
  4. Returns only safe metadata (entity types + positions) — never
     the actual sensitive values.

Presidio entity types we use:
  PERSON, EMAIL_ADDRESS, PHONE_NUMBER, CREDIT_CARD, IBAN_CODE,
  CRYPTO, US_SSN, US_PASSPORT, IP_ADDRESS, URL, DATE_TIME, NRP,
  LOCATION, MEDICAL_LICENSE, US_BANK_NUMBER, US_DRIVER_LICENSE,
  plus custom: API_KEY, ACCESS_TOKEN, PASSWORD_LIKE

NOTE: Detection is best-effort. Presidio has known false-positive and
      false-negative rates that vary by entity type and text context.
      This system does NOT claim perfect recall or precision.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider

from app.core.config import settings

# ────────────────────────────────────────────────────────────────────
# Custom regex recognizers
# ────────────────────────────────────────────────────────────────────
# Explanation of each pattern:
#
#  API_KEY:        Generic high-entropy key-like strings seen in common
#                  services (AWS, GCP, Stripe, GitHub PAT, etc.).
#                  Pattern heuristic: 20+ character base-64/hex token
#                  that follows a key= or key: assignment.
#
#  ACCESS_TOKEN:   Bearer / OAuth tokens that typically appear in
#                  Authorization headers or config files.
#
#  PASSWORD_LIKE:  Literal password assignments in config snippets
#                  (password=..., passwd=..., pwd=...).
#
# These patterns are intentionally conservative to limit false positives.
# Adjust confidence scores downward (e.g. 0.5) if they fire too broadly.

_API_KEY_PATTERNS = [
    # AWS access key ID: AKIA[A-Z0-9]{16}
    Pattern(name="aws_access_key", regex=r"\bAKIA[A-Z0-9]{16}\b", score=0.9),
    # Generic high-entropy token after key=/key: (20–80 chars, mixed)
    Pattern(
        name="generic_api_key",
        regex=r'(?i)(?:api[_\-]?key|apikey|access[_\-]?key)\s*[=:]\s*["\']?([A-Za-z0-9\-_\.]{20,80})["\']?',
        score=0.75,
    ),
    # GitHub personal access token
    Pattern(name="github_pat", regex=r"\bghp_[A-Za-z0-9]{36}\b", score=0.95),
    # Stripe secret key
    Pattern(name="stripe_key", regex=r"\bsk_(?:live|test)_[A-Za-z0-9]{24,}\b", score=0.95),
    # Google API key
    Pattern(name="google_api_key", regex=r"\bAIza[0-9A-Za-z\-_]{35}\b", score=0.9),
]

_ACCESS_TOKEN_PATTERNS = [
    # Bearer token in Authorization header value
    Pattern(
        name="bearer_token",
        regex=r'(?i)(?:Bearer\s+)([A-Za-z0-9\-_\.]{20,})',
        score=0.85,
    ),
    # JWT token structure: three base64url segments separated by dots
    Pattern(
        name="jwt_token",
        regex=r'\b(eyJ[A-Za-z0-9\-_]{10,}\.[A-Za-z0-9\-_]{10,}\.[A-Za-z0-9\-_]{10,})\b',
        score=0.9,
    ),
]

_PASSWORD_PATTERNS = [
    # password=value, passwd=value, pwd=value (case-insensitive)
    Pattern(
        name="password_assignment",
        regex=r'(?i)(?:password|passwd|pwd)\s*[=:]\s*["\']?([^\s"\']{4,})["\']?',
        score=0.8,
    ),
    # Secret assignments
    Pattern(
        name="secret_assignment",
        regex=r'(?i)(?:secret|client_secret)\s*[=:]\s*["\']?([A-Za-z0-9\-_\.]{8,})["\']?',
        score=0.75,
    ),
]

_custom_recognizers = [
    PatternRecognizer(
        supported_entity="API_KEY",
        patterns=_API_KEY_PATTERNS,
        context=["key", "api", "token", "access"],
    ),
    PatternRecognizer(
        supported_entity="ACCESS_TOKEN",
        patterns=_ACCESS_TOKEN_PATTERNS,
        context=["bearer", "token", "authorization", "jwt"],
    ),
    PatternRecognizer(
        supported_entity="PASSWORD_LIKE",
        patterns=_PASSWORD_PATTERNS,
        context=["password", "passwd", "pwd", "secret"],
    ),
]

# ────────────────────────────────────────────────────────────────────
# Entity severity weights
# (used by the risk scorer — defined here for single source of truth)
# ────────────────────────────────────────────────────────────────────
# Scale: 0.0 (benign) to 1.0 (most critical).
# These weights are documented choices, not statistically calibrated values.
ENTITY_SEVERITY: Dict[str, float] = {
    # Credentials — highest risk because they grant direct access
    "API_KEY": 1.0,
    "ACCESS_TOKEN": 1.0,
    "PASSWORD_LIKE": 1.0,
    # Financial identifiers — high risk
    "CREDIT_CARD": 0.9,
    "IBAN_CODE": 0.85,
    "US_BANK_NUMBER": 0.85,
    "CRYPTO": 0.8,
    # Government identifiers
    "US_SSN": 0.9,
    "US_PASSPORT": 0.85,
    "US_DRIVER_LICENSE": 0.75,
    "MEDICAL_LICENSE": 0.7,
    # Personal contact info
    "EMAIL_ADDRESS": 0.6,
    "PHONE_NUMBER": 0.6,
    "PERSON": 0.5,
    # Location / network
    "LOCATION": 0.4,
    "IP_ADDRESS": 0.5,
    "URL": 0.2,
    # Temporal / generic
    "DATE_TIME": 0.15,
    "NRP": 0.3,
    # Fallback for any unlisted entity
    "_DEFAULT": 0.4,
}


@dataclass
class DetectionResult:
    """Safe output of the PII detector.

    Contains ONLY metadata — never the actual detected values.
    """
    detected_entities: List[str] = field(default_factory=list)
    entity_counts: Dict[str, int] = field(default_factory=dict)
    # Internal use only — NOT exposed to the API response.
    # Stores (start, end, entity_type, score) so the redactor can mask spans.
    _raw_results: List[RecognizerResult] = field(default_factory=list, repr=False)
    has_sensitive_content: bool = False


# ────────────────────────────────────────────────────────────────────
# Detector service (singleton-style lazy init)
# ────────────────────────────────────────────────────────────────────

_analyzer: Optional[AnalyzerEngine] = None


def _build_analyzer() -> AnalyzerEngine:
    """
    Build a Presidio AnalyzerEngine with spaCy and custom recognizers.

    Required model: en_core_web_sm
    Install with: python -m spacy download en_core_web_sm
    """
    provider = NlpEngineProvider(
        nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [
                {"lang_code": "en", "model_name": "en_core_web_sm"}
            ],
        }
    )
    nlp_engine = provider.create_engine()

    analyzer = AnalyzerEngine(
        nlp_engine=nlp_engine,
        supported_languages=["en"],
    )

    # Register custom recognizers
    for recognizer in _custom_recognizers:
        analyzer.registry.add_recognizer(recognizer)

    return analyzer


def get_analyzer() -> AnalyzerEngine:
    """Return the shared AnalyzerEngine, initialising it on first call."""
    global _analyzer
    if _analyzer is None:
        _analyzer = _build_analyzer()
    return _analyzer


def detect(text: str, language: str = "en") -> DetectionResult:
    """
    Analyse *text* for sensitive entities and return safe metadata.

    Args:
        text:     The input text to analyse (may be a chat message or
                  extracted document content).
        language: ISO 639-1 language code (default: "en").

    Returns:
        DetectionResult with entity types, counts and internal spans.
        The actual sensitive text values are never returned.
    """
    if not text or not text.strip():
        return DetectionResult()

    analyzer = get_analyzer()
    threshold = settings.PII_CONFIDENCE_THRESHOLD

    raw: List[RecognizerResult] = analyzer.analyze(
        text=text,
        language=language,
        score_threshold=threshold,
        # Request ALL entity types so nothing is silently skipped.
        entities=None,
    )

    # Build safe metadata
    counts: Dict[str, int] = {}
    for result in raw:
        counts[result.entity_type] = counts.get(result.entity_type, 0) + 1

    detected_entities = sorted(counts.keys())

    return DetectionResult(
        detected_entities=detected_entities,
        entity_counts=counts,
        _raw_results=raw,
        has_sensitive_content=len(raw) > 0,
    )
