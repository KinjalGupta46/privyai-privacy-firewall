"""
app/services/output_scanner.py

Output scanning service.

After the LLM generates a response, this service checks whether the
response contains sensitive information before it is returned to the user.

Why output scanning matters:
  - The LLM may hallucinate sensitive-looking content (e.g. fake SSNs).
  - Some prompts could trick the model into reproducing redacted content.
  - We apply the same privacy pipeline to the output as to the input.

This is a best-effort check. It does not guarantee the output is
completely free of sensitive information — detection has inherent limits.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.pii_detector import DetectionResult, detect
from app.services.redaction import RedactionResult, redact
from app.services.risk_scoring import ALLOW, BLOCK, REDACT, RiskResult, score


@dataclass
class OutputScanResult:
    """Result of scanning the LLM's response."""
    original_text: str          # Never returned to frontend
    safe_text: str              # Redacted version (returned to frontend)
    action: str                 # ALLOW | REDACT | BLOCK
    risk_result: RiskResult
    redaction_result: RedactionResult | None = None


def scan_output(llm_response_text: str) -> OutputScanResult:
    """
    Scan the LLM's response text for sensitive content and apply policy.

    Args:
        llm_response_text: The raw text returned by the LLM provider.

    Returns:
        OutputScanResult with the safe version of the text and action taken.
        The original_text field is for internal audit only and must not be
        sent to the frontend.
    """
    detection: DetectionResult = detect(llm_response_text)
    risk: RiskResult = score(detection)

    if risk.action == ALLOW:
        return OutputScanResult(
            original_text=llm_response_text,
            safe_text=llm_response_text,
            action=ALLOW,
            risk_result=risk,
        )

    elif risk.action == REDACT:
        redaction: RedactionResult = redact(llm_response_text, detection)
        return OutputScanResult(
            original_text=llm_response_text,
            safe_text=redaction.redacted_text,
            action=REDACT,
            risk_result=risk,
            redaction_result=redaction,
        )

    else:  # BLOCK
        return OutputScanResult(
            original_text=llm_response_text,
            safe_text=(
                "[Response blocked by privacy policy. "
                "The generated content contained high-risk sensitive information.]"
            ),
            action=BLOCK,
            risk_result=risk,
        )
