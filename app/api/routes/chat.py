"""
app/api/routes/chat.py

POST /api/chat — Main privacy-firewall endpoint.

Pipeline (in order):
  1. Validate input length and format (Pydantic).
  2. Detect sensitive entities (Presidio + custom rules).
  3. Score risk (soft-max heuristic).
  4. Apply privacy policy: ALLOW / REDACT / BLOCK.
  5. If BLOCK → return error immediately, never call the LLM.
  6. Redact every detected sensitive entity before calling the LLM.
  7. Call the LLM with the sanitised prompt only.
  8. Scan the LLM's response for sensitive content.
  9. Apply output policy (ALLOW / REDACT / BLOCK).
 10. Persist safe scan metadata to the database (if configured).
 11. Return the safe response and privacy metadata.

Privacy guarantee: Detected sensitive content is redacted before the
original prompt is sent to the LLM. Detection has inherent limitations.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from app.core.security import generate_request_id
from app.schemas.chat import ChatRequest, ChatResponse
from app.services import (
    llm_service,
    output_scanner,
    pii_detector,
    redaction,
    risk_scoring,
)
from app.services.privacy_policy import BLOCK, REDACT
from app.utils.exceptions import RequestBlockedError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Privacy-filtered chat",
    description=(
        "Sends a message through the PrivyAI privacy pipeline. "
        "Sensitive content is detected, scored, and redacted or blocked "
        "before reaching the LLM. The LLM response is also scanned."
    ),
    tags=["Chat"],
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Main privacy-firewall endpoint.
    See module docstring for the full pipeline description.
    """
    request_id = generate_request_id()

    # Step 1: Input is validated by Pydantic.

    # Steps 2 and 3: Detect sensitive entities and score risk.
    detection = pii_detector.detect(request.message)
    risk = risk_scoring.score(detection)

    # Steps 4 and 5: Block high-risk input immediately.
    if risk.action == BLOCK:
        logger.warning(
            "Request BLOCKED | request_id=%s | score=%.2f | entities=%s",
            request_id,
            risk.risk_score,
            risk.detected_entities,
        )
        _persist_scan(
            request_id=request_id,
            risk=risk,
            output_action="N/A",
            input_action=BLOCK,
        )
        raise RequestBlockedError(
            f"Request blocked by privacy policy. "
            f"Risk score: {risk.risk_score:.2f}. "
            f"Detected categories: "
            f"{', '.join(risk.detected_entities) or 'N/A'}."
        )

    # Step 6: Redact all detected sensitive content before sending it
    # to the LLM, even if the risk score would otherwise allow it.
    if detection.has_sensitive_content:
        redaction_result = redaction.redact(request.message, detection)
        prompt_to_send = redaction_result.redacted_text
        effective_action = REDACT
    else:
        prompt_to_send = request.message
        effective_action = risk.action

    # Step 7: Call the LLM with the sanitised prompt only.
    llm_response = await llm_service.call_llm(prompt_to_send)

    # Steps 8 and 9: Scan and apply the output privacy policy.
    output_scan = output_scanner.scan_output(llm_response.text)
    safe_response_text = output_scan.safe_text

    # Step 10: Persist metadata only, never raw prompt or response text.
    _persist_scan(
        request_id=request_id,
        risk=risk,
        output_action=output_scan.action,
        input_action=effective_action,
    )

    logger.info(
        "Request processed | request_id=%s | action=%s | score=%.2f | "
        "output_action=%s",
        request_id,
        effective_action,
        risk.risk_score,
        output_scan.action,
    )

    # Step 11: Return the safe response and privacy metadata.
    return ChatResponse(
        response=safe_response_text,
        action=effective_action,
        detected_entities=risk.detected_entities,
        entity_counts=risk.entity_counts,
        risk_score=risk.risk_score,
        output_action=output_scan.action,
        request_id=request_id,
        mock=llm_response.mock,
    )


def _persist_scan(
    request_id: str,
    risk: risk_scoring.RiskResult,
    output_action: str,
    input_action: str | None = None,
) -> None:
    """
    Persist safe scan metadata to the database.

    Only entity types, counts, scores and actions are stored.
    The original prompt, redacted text and LLM response are never stored.

    If the database is unavailable, log a warning and continue because
    scan history is non-critical for the privacy guarantee.
    """
    try:
        from app.db.session import get_db_session
        from app.db.models.privacy_scan import PrivacyScanModel

        with get_db_session() as session:
            scan = PrivacyScanModel(
                request_id=request_id,
                detected_entity_types=risk.detected_entities,
                entity_counts=risk.entity_counts,
                action_taken=input_action or risk.action,
                risk_score=risk.risk_score,
                output_action=output_action,
            )
            session.add(scan)
            session.commit()
    except Exception as exc:
        # Database failure must not expose prompt content or block the response.
        logger.warning(
            "Could not persist scan metadata: %s",
            type(exc).__name__,
        )
