"""
app/api/routes/scans.py

Audit logs and privacy telemetry endpoints.
Exposes scan metrics and historical audit events stored in PostgreSQL
for the frontend dashboard.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.db.session import get_db_session
from app.db.models import PrivacyScanModel, AuditLogModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scans", tags=["Scans"])


class TelemetrySummary(BaseModel):
    total_scans: int
    allowed_count: int
    redacted_count: int
    blocked_count: int
    avg_risk_score: float
    scans: List[Dict[str, Any]]
    recent_audit_logs: List[Dict[str, Any]]


@router.get("", response_model=TelemetrySummary)
async def get_scans(limit: int = 50) -> TelemetrySummary:
    """Fetch scan history and audit telemetry."""
    if not settings.DATABASE_URL:
        return TelemetrySummary(
            total_scans=0,
            allowed_count=0,
            redacted_count=0,
            blocked_count=0,
            avg_risk_score=0.0,
            scans=[],
            recent_audit_logs=[],
        )

    try:
        with get_db_session() as session:
            scans = (
                session.query(PrivacyScanModel)
                .order_by(PrivacyScanModel.created_at.desc())
                .limit(limit)
                .all()
            )

            total = len(scans)
            allowed = sum(1 for s in scans if s.action_taken == "ALLOW")
            redacted = sum(1 for s in scans if s.action_taken == "REDACT")
            blocked = sum(1 for s in scans if s.action_taken == "BLOCK")
            avg_score = (
                round(sum((s.risk_score or 0.0) for s in scans) / total, 3)
                if total > 0
                else 0.0
            )

            scan_records = [
                {
                    "id": s.id,
                    "request_id": s.request_id,
                    "action_taken": s.action_taken,
                    "risk_score": s.risk_score,
                    "output_action": s.output_action,
                    "detected_entity_types": s.detected_entity_types or [],
                    "entity_counts": s.entity_counts or {},
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in scans
            ]

            audit_logs = (
                session.query(AuditLogModel)
                .order_by(AuditLogModel.created_at.desc())
                .limit(30)
                .all()
            )

            audit_records = [
                {
                    "id": a.id,
                    "scan_id": a.scan_id,
                    "event_type": a.event_type,
                    "status": a.status,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in audit_logs
            ]

            return TelemetrySummary(
                total_scans=total,
                allowed_count=allowed,
                redacted_count=redacted,
                blocked_count=blocked,
                avg_risk_score=avg_score,
                scans=scan_records,
                recent_audit_logs=audit_records,
            )

    except Exception as exc:
        logger.warning("Could not query scans telemetry: %s", type(exc).__name__)
        return TelemetrySummary(
            total_scans=0,
            allowed_count=0,
            redacted_count=0,
            blocked_count=0,
            avg_risk_score=0.0,
            scans=[],
            recent_audit_logs=[],
        )
