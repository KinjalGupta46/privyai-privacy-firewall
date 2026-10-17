"""
app/services/redaction.py

Text redaction service using Presidio's AnonymizerEngine.

What it does:
  - Takes the original text and the raw detection results from pii_detector.
  - Replaces each detected sensitive span with a placeholder like <EMAIL_ADDRESS>.
  - Returns the redacted text and a count of redacted entities.

Design choices:
  - We use REPLACE anonymization (e.g. <ENTITY_TYPE>) rather than masking
    with * characters. This retains sentence structure and makes the result
    more useful for an LLM prompt.
  - The original text is NEVER returned; only the redacted version is.
  - We do not log, store or expose any original sensitive values.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig, RecognizerResult

from app.services.pii_detector import DetectionResult

# Single shared instance of the anonymizer — it is thread-safe.
_anonymizer = AnonymizerEngine()


@dataclass
class RedactionResult:
    """Output of the redaction service."""
    redacted_text: str
    # How many spans were replaced per entity type.
    redacted_counts: Dict[str, int]
    # Total number of replaced spans.
    total_redacted: int


def redact(text: str, detection: DetectionResult) -> RedactionResult:
    """
    Replace all detected sensitive spans in *text* with safe placeholders.

    Each entity type gets a placeholder in the form <ENTITY_TYPE>, e.g.:
      - Email "alice@example.com" → <EMAIL_ADDRESS>
      - API key "sk_live_abc123" → <API_KEY>
      - Phone "+44 7911 123456" → <PHONE_NUMBER>

    Args:
        text:      The original text (must match what was passed to detect()).
        detection: The DetectionResult from pii_detector.detect().

    Returns:
        RedactionResult with the masked text and redaction statistics.
    """
    if not detection.has_sensitive_content or not detection._raw_results:
        return RedactionResult(
            redacted_text=text,
            redacted_counts={},
            total_redacted=0,
        )

    # Build an operator config that replaces every entity type with
    # a bracketed placeholder.  The entity_type value is substituted
    # automatically by Presidio's REPLACE operator.
    operators = {
        entity_type: OperatorConfig("replace", {"new_value": f"<{entity_type}>"})
        for entity_type in detection.entity_counts
    }
    # Fallback for any entity type not explicitly configured
    operators["DEFAULT"] = OperatorConfig("replace", {"new_value": "<REDACTED>"})

    anonymized = _anonymizer.anonymize(
        text=text,
        analyzer_results=detection._raw_results,
        operators=operators,
    )

    return RedactionResult(
        redacted_text=anonymized.text,
        redacted_counts=dict(detection.entity_counts),
        total_redacted=sum(detection.entity_counts.values()),
    )
