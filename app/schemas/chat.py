"""
app/schemas/chat.py

Pydantic request and response schemas for the /api/chat endpoint.

Coordinate with the frontend team before changing field names.
These schemas define the API contract.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.core.config import settings


class ChatRequest(BaseModel):
    """Request body for POST /api/chat."""
    message: str = Field(
        ...,
        min_length=1,
        description="The user's chat message or prompt.",
        examples=["Summarize this customer information for me."],
    )

    @field_validator("message")
    @classmethod
    def _check_length(cls, v: str) -> str:
        max_len = settings.MAX_MESSAGE_LENGTH
        if len(v) > max_len:
            raise ValueError(f"Message exceeds maximum length of {max_len} characters.")
        return v


class ChatResponse(BaseModel):
    """Response body for POST /api/chat.

    Field contract (do not rename without coordinating with the frontend):
      response           — The safe (possibly redacted) text to display.
      action             — Input-scan decision: ALLOW | REDACT | BLOCK.
      detected_entities  — List of entity type names detected in the input.
      entity_counts      — Count of each entity type detected.
      risk_score         — Heuristic risk score (0.0–1.0). NOT a probability.
      output_action      — Output-scan decision: ALLOW | REDACT | BLOCK.
      request_id         — UUID for tracing this request in logs.
      mock               — True if the response came from the mock LLM.
    """
    response: str
    action: str
    detected_entities: List[str]
    entity_counts: Dict[str, int]
    risk_score: float
    output_action: str
    request_id: str
    mock: bool = False

    model_config = {"json_schema_extra": {
        "example": {
            "response": "Here is the summary with sensitive data removed.",
            "action": "REDACT",
            "detected_entities": ["EMAIL_ADDRESS"],
            "entity_counts": {"EMAIL_ADDRESS": 1},
            "risk_score": 0.52,
            "output_action": "ALLOW",
            "request_id": "550e8400-e29b-41d4-a716-446655440000",
            "mock": False,
        }
    }}
