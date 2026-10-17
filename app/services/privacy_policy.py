"""
app/services/privacy_policy.py

Privacy policy decision helpers.

This module re-exports the policy constants and provides a helper that
makes the final decision combining input and output scan results.
It is intentionally thin — the logic lives in risk_scoring.py.
"""

from __future__ import annotations

from app.services.risk_scoring import ALLOW, BLOCK, REDACT, RiskResult

__all__ = ["ALLOW", "REDACT", "BLOCK", "PolicyDecision"]


class PolicyDecision:
    """Container for the combined input + output policy decision."""

    def __init__(
        self,
        input_result: RiskResult,
        output_result: RiskResult | None = None,
    ) -> None:
        self.input_result = input_result
        self.output_result = output_result

    @property
    def input_action(self) -> str:
        return self.input_result.action

    @property
    def output_action(self) -> str:
        if self.output_result is None:
            return ALLOW
        return self.output_result.action

    @property
    def blocked_at_input(self) -> bool:
        return self.input_action == BLOCK

    @property
    def safe_to_return(self) -> bool:
        """True if the output response can be returned to the frontend."""
        return self.output_action != BLOCK
