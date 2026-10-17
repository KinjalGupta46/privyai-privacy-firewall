
"""
app/services/output_scanner.py

Output scanning service.

After the LLM generates a response, this service checks whether the
response contains sensitive information before it is returned to the user.

Why output scanning matters:
  - The LLM may hallucinate sensitive-looking content (e.g. fake SSNs).
  - Some prompts could trick the model into reproducing redacted content.
  - We apply the same privacy pipeline to the output as to the input.

This is a best-effort check. It does not guarantee that the response is
completely free of sensitive information because detection has limitations.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.pii_detector import DetectionResult, detect
from app.services.redaction import RedactionResult, redact
from app.services.risk_scoring import ALLOW, BLOCK, REDACT, RiskResult, score


@dataclass
class OutputScanResult:
    """Result of scanning the LLM's response."""

    original_text: str  # Must never be returned to the frontend
    safe_text: str
    action: str  # ALLOW | REDACT | BLOCK
    risk_result: RiskResult
    redaction_result: RedactionResult | None = None


def scan_output(llm_response_text: str) -> OutputScanResult:
    """
    Scan the LLM response and apply the output privacy policy.

    The original response is retained in this internal result for processing,
    but callers must return only safe_text to the frontend.
    """
    detection: DetectionResult = detect(llm_response_text)
    risk: RiskResult = score(detection)

    # Block high-risk output before returning any of its content.
    if risk.action == BLOCK:
        return OutputScanResult(
            original_text=llm_response_text,
            safe_text=(
                "[Response blocked by privacy policy. "
                "The generated content contained high-risk sensitive information.]"
            ),
            action=BLOCK,
            risk_result=risk,
        )

    # Return unchanged only if no sensitive entities were detected.
    if not detection.has_sensitive_content:
        return OutputScanResult(
            original_text=llm_response_text,
            safe_text=llm_response_text,
            action=ALLOW,
            risk_result=risk,
        )

    # Redact detected entities even if the risk score would otherwise ALLOW.
    redaction_result: RedactionResult = redact(
        llm_response_text,
        detection,
    )

    return OutputScanResult(
        original_text=llm_response_text,
        safe_text=redaction_result.redacted_text,
        action=REDACT,
        risk_result=risk,
        redaction_result=redaction_result,
    )
