"""
app/api/routes/documents.py

Document upload, parsing, and privacy inspection endpoints.
Coordinates file storage, text extraction, and PII firewall scanning.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.config import settings
from app.db.session import get_db_session
from app.db.models.document import DocumentModel
from app.services.document_parser import extract_text
from app.services.storage import storage_service
from app.services import pii_detector, risk_scoring, redaction, llm_service
from app.services.privacy_policy import BLOCK, REDACT

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["Documents"])


class DocumentScanResponse(BaseModel):
    id: Optional[int] = None
    filename: str
    storage_key: str
    size_bytes: int
    char_count: int
    text_preview: str
    action: str
    risk_score: float
    detected_entities: List[str]
    entity_counts: dict[str, int]
    raw_text: Optional[str] = None


class DocumentChatRequest(BaseModel):
    query: str


class DocumentChatResponse(BaseModel):
    response: str
    action: str
    risk_score: float
    detected_entities: List[str]


@router.post("/upload", response_model=DocumentScanResponse)
async def upload_document(file: UploadFile = File(...)) -> DocumentScanResponse:
    """
    Upload a document (PDF, DOCX, TXT), store it securely, extract text,
    and run it through the privacy scanning pipeline.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty.")

    # 1. Save file to storage
    storage_key, size_bytes = storage_service.save_file(
        file.file,
        original_filename=file.filename,
        content_type=file.content_type,
    )

    file_path = storage_service.get_file_path(storage_key)
    if not file_path:
        raise HTTPException(status_code=500, detail="Could not locate saved file.")

    # 2. Extract text from document
    extracted_text = extract_text(file_path)

    # 3. Scan extracted text for PII / sensitive data
    detection = pii_detector.detect(extracted_text)
    risk = risk_scoring.score(detection)

    # 4. Save to Database if configured
    doc_id = None
    if settings.DATABASE_URL:
        try:
            with get_db_session() as session:
                doc = DocumentModel(
                    filename=file.filename,
                    storage_key=storage_key,
                )
                session.add(doc)
                session.commit()
                doc_id = doc.id
        except Exception as exc:
            logger.warning("Could not persist document model to DB: %s", type(exc).__name__)

    return DocumentScanResponse(
        id=doc_id,
        filename=file.filename,
        storage_key=storage_key,
        size_bytes=size_bytes,
        char_count=len(extracted_text),
        text_preview=extracted_text[:400] + ("..." if len(extracted_text) > 400 else ""),
        action=risk.action,
        risk_score=risk.risk_score,
        detected_entities=risk.detected_entities,
        entity_counts=risk.entity_counts,
        raw_text=extracted_text,
    )


@router.get("", response_model=List[dict])
async def list_documents() -> List[dict]:
    """List uploaded documents."""
    if not settings.DATABASE_URL:
        # Fallback if DB is not configured: list files in storage directory
        import os
        results = []
        if storage_service.base_path.exists():
            for p in storage_service.base_path.iterdir():
                if p.is_file():
                    results.append({
                        "id": None,
                        "filename": p.name,
                        "storage_key": p.name,
                        "size_bytes": p.stat().st_size,
                        "created_at": None,
                    })
        return results

    try:
        with get_db_session() as session:
            docs = session.query(DocumentModel).order_by(DocumentModel.created_at.desc()).all()
            return [
                {
                    "id": d.id,
                    "filename": d.filename,
                    "storage_key": d.storage_key,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                }
                for d in docs
            ]
    except Exception as exc:
        logger.warning("Could not fetch documents from DB: %s", type(exc).__name__)
        return []


@router.delete("/{storage_key}")
async def delete_document(storage_key: str):
    """Delete a document by its storage key."""
    storage_service.delete_file(storage_key)
    if settings.DATABASE_URL:
        try:
            with get_db_session() as session:
                doc = session.query(DocumentModel).filter(DocumentModel.storage_key == storage_key).first()
                if doc:
                    session.delete(doc)
                    session.commit()
        except Exception as exc:
            logger.warning("Could not delete document from DB: %s", type(exc).__name__)

    return {"status": "deleted", "storage_key": storage_key}
