"""
app/api/routes/chat.py

POST /api/chat — Main privacy-firewall endpoint.

Pipeline (in order):
  1. Validate input length and format (Pydantic).
  2. Detect sensitive entities (Presidio + custom rules).
  3. Score risk (soft-max heuristic).
  4. Apply privacy policy: ALLOW / REDACT / BLOCK.
  5. If BLOCK → return error immediately, never call the LLM.
  6. If REDACT → redact the prompt.
  7. Call the LLM with the sanitised prompt only.
  8. Scan the LLM's response for sensitive content.
  9. Apply output policy (ALLOW / REDACT / BLOCK).
 10. Persist safe scan metadata to the database (if configured).
 11. Return the safe response and privacy metadata.

Privacy guarantee: The original unredacted prompt is NEVER sent to the LLM.
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

    # ── Step 1: Input already validated by Pydantic ──────────────────

    # ── Step 2 & 3: Detect + score ───────────────────────────────────
    detection = pii_detector.detect(request.message)
    risk = risk_scoring.score(detection)

    # ── Step 4 & 5: Policy decision ──────────────────────────────────
    if risk.action == BLOCK:
        # NEVER call the LLM. Log only safe metadata — no prompt content.
        logger.warning(
            "Request BLOCKED | request_id=%s | score=%.2f | entities=%s",
            request_id, risk.risk_score, risk.detected_entities,
        )
        _persist_scan(
            request_id=request_id,
            risk=risk,
            output_action="N/A",
        )
        raise RequestBlockedError(
            f"Request blocked by privacy policy. "
            f"Risk score: {risk.risk_score:.2f}. "
            f"Detected categories: {', '.join(risk.detected_entities) or 'N/A'}."
        )

    # ── Step 6: Redact if needed ─────────────────────────────────────
    if risk.action == REDACT:
        redaction_result = redaction.redact(request.message, detection)
        prompt_to_send = redaction_result.redacted_text
    else:
        # ALLOW — no sensitive content detected
        prompt_to_send = request.message

    # ── Step 7: Call LLM (sanitised prompt only) ─────────────────────
    llm_response = await llm_service.call_llm(prompt_to_send)

    # ── Step 8 & 9: Output scanning ──────────────────────────────────
    output_scan = output_scanner.scan_output(llm_response.text)
    safe_response_text = output_scan.safe_text

    # ── Step 10: Persist audit metadata ──────────────────────────────
    _persist_scan(
        request_id=request_id,
        risk=risk,
        output_action=output_scan.action,
    )

    # ── Step 11: Return safe response ────────────────────────────────
    logger.info(
        "Request processed | request_id=%s | action=%s | score=%.2f | output_action=%s",
        request_id, risk.action, risk.risk_score, output_scan.action,
    )

    return ChatResponse(
        response=safe_response_text,
        action=risk.action,
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
) -> None:
    """
    Persist safe scan metadata to the database.

    Only entity types, counts, scores and actions are stored.
    The original prompt, redacted text and LLM response are NEVER stored.

    If the database is unavailable, this silently logs a warning and
    continues — scan history is non-critical for the privacy guarantee.
    """
    try:
        from app.db.session import get_db_session
        from app.db.models.privacy_scan import PrivacyScanModel

        with get_db_session() as session:
            scan = PrivacyScanModel(
                request_id=request_id,
                detected_entity_types=risk.detected_entities,
                entity_counts=risk.entity_counts,
                action_taken=risk.action,
                risk_score=risk.risk_score,
                output_action=output_action,
            )
            session.add(scan)
            session.commit()
    except Exception as exc:
        # Non-fatal: DB unavailable should not block the privacy response.
        logger.warning("Could not persist scan metadata: %s", type(exc).__name__)
