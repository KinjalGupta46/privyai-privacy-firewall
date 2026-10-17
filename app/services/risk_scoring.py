"""
app/services/risk_scoring.py

Transparent risk scoring and privacy-policy engine.

## How the score is calculated

1. For each detected entity, look up its severity weight from ENTITY_SEVERITY.
   Severity values range from 0 (benign) to 1.0 (maximum risk).

2. Multiply the severity by Presidio's detection confidence (0.0–1.0).
   This penalises low-confidence detections and rewards high-confidence ones.
   weighted_score_i = severity_i × confidence_i

3. Combine all entity scores using a "soft-max" formula:
   combined = 1 - ∏(1 - weighted_score_i)
   This means: adding more risky entities increases the score toward 1,
   but a single low-severity entity alone cannot push it past ~0.5.

4. Normalise to [0, 1]. The value is already in [0, 1] from step 3.

5. Apply configurable thresholds from .env / settings:
   score < RISK_ALLOW_THRESHOLD  → ALLOW
   score < RISK_REDACT_THRESHOLD → REDACT
   score >= RISK_REDACT_THRESHOLD → BLOCK

## Important caveats
- This score is NOT a statistically calibrated probability.
- It is a deterministic, explainable heuristic designed for demonstration.
- Threshold values are initial reasonable defaults; tune them after evaluation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List

from presidio_analyzer import RecognizerResult

from app.core.config import settings
from app.services.pii_detector import ENTITY_SEVERITY, DetectionResult

# Policy decision labels
ALLOW = "ALLOW"
REDACT = "REDACT"
BLOCK = "BLOCK"


@dataclass
class RiskResult:
    """Output of the risk scorer."""
    risk_score: float               # 0.0 – 1.0
    action: str                     # ALLOW | REDACT | BLOCK
    detected_entities: List[str]    # Safe: entity type names only
    entity_counts: Dict[str, int]   # Safe: counts per entity type
    # Explanation is safe to return to the frontend (no sensitive values).
    explanation: str


def score(detection: DetectionResult) -> RiskResult:
    """
    Compute a risk score and policy decision for a detection result.

    Args:
        detection: Output of pii_detector.detect().

    Returns:
        RiskResult with score in [0.0, 1.0] and an action string.
    """
    if not detection.has_sensitive_content:
        return RiskResult(
            risk_score=0.0,
            action=ALLOW,
            detected_entities=[],
            entity_counts={},
            explanation="No sensitive entities detected.",
        )

    # Step 1 & 2: Compute per-entity weighted scores.
    weighted_scores: List[float] = []
    for result in detection._raw_results:
        severity = ENTITY_SEVERITY.get(result.entity_type, ENTITY_SEVERITY["_DEFAULT"])
        weighted = severity * result.score   # confidence comes from Presidio
        weighted_scores.append(min(weighted, 1.0))

    # Step 3: Soft-max combination.
    # 1 - product of (1 - each score)
    # E.g. two entities with weight 0.5 each → 1 - (0.5)(0.5) = 0.75
    combined = 1.0 - math.prod(1.0 - w for w in weighted_scores)
    risk_score = round(min(combined, 1.0), 4)

    # Step 4: Policy decision based on configured thresholds.
    allow_t = settings.RISK_ALLOW_THRESHOLD
    redact_t = settings.RISK_REDACT_THRESHOLD

    if risk_score < allow_t:
        action = ALLOW
    elif risk_score < redact_t:
        action = REDACT
    else:
        action = BLOCK

    # Build a safe, human-readable explanation.
    top_entities = sorted(
        detection.entity_counts.items(),
        key=lambda kv: ENTITY_SEVERITY.get(kv[0], 0),
        reverse=True,
    )
    entity_summary = ", ".join(f"{et} ({cnt})" for et, cnt in top_entities[:5])
    explanation = (
        f"Risk score: {risk_score:.2f}. "
        f"Action: {action}. "
        f"Detected entity types: {entity_summary or 'none'}. "
        f"Thresholds — ALLOW:<{allow_t} | REDACT:{allow_t}–{redact_t} | BLOCK:≥{redact_t}."
    )

    return RiskResult(
        risk_score=risk_score,
        action=action,
        detected_entities=detection.detected_entities,
        entity_counts=detection.entity_counts,
        explanation=explanation,
    )
