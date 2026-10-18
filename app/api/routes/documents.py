"""
app/api/routes/documents.py

Document upload, parsing, and privacy inspection endpoints.
Coordinates file storage, text extraction, and PII firewall scanning.

Every upload is recorded in the `documents` table with its file path,
size and processing status, and can be retrieved later via:
    GET /api/documents            -> list (filter by status, paginate)
    GET /api/documents/{id}       -> one document's stored metadata
    POST /api/documents/{id}/scan -> re-run text extraction + PII scan on the stored file

Access control: when DOCUMENT_API_KEYS is configured every endpoint requires an
X-API-Key header and only touches the caller's own documents (see app/core/access.py).
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.core.access import get_current_user_id
from app.core.config import settings
from app.core.security import sanitize_filename
from app.db.models.document import (
    DOC_STATUS_FAILED,
    DOC_STATUS_SCANNED,
    DOC_STATUS_UPLOADED,
    DOCUMENT_STATUSES,
    DocumentModel,
)
from app.db.session import get_db_session
from app.services import pii_detector, risk_scoring
from app.services.document_parser import extract_text
from app.services.storage import storage_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["Documents"])


class DocumentScanResponse(BaseModel):
    id: Optional[int] = None
    filename: str
    storage_key: str
    file_path: Optional[str] = None
    status: str = DOC_STATUS_UPLOADED
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


# ------------------------------------------------------------------ #
# DB helpers (the database is optional — failures never break uploads)  #
# ------------------------------------------------------------------ #
def _create_document_record(
    filename: str,
    storage_key: str,
    file_path: str,
    size_bytes: int,
    user_id: Optional[int] = None,
) -> Optional[int]:
    """Insert a row for a freshly stored file. Returns its id, or None."""
    if not settings.DATABASE_URL:
        return None
    try:
        with get_db_session() as session:
            doc = DocumentModel(
                user_id=user_id,
                filename=filename,
                storage_key=storage_key,
                file_path=file_path,
                size_bytes=size_bytes,
                status=DOC_STATUS_UPLOADED,
            )
            session.add(doc)
            session.flush()  # populate doc.id before the commit
            return doc.id
    except Exception as exc:
        logger.warning("Could not persist document to DB: %s", type(exc).__name__)
        return None


def _set_document_status(doc_id: Optional[int], status: str) -> None:
    """Update the processing status of a stored document."""
    if doc_id is None or not settings.DATABASE_URL:
        return
    try:
        with get_db_session() as session:
            doc = session.get(DocumentModel, doc_id)
            if doc:
                doc.status = status
    except Exception as exc:
        logger.warning("Could not update document status: %s", type(exc).__name__)


def _process_file(file_path):
    """Extract text from a stored file and run the PII scan. Returns (text, risk)."""
    extracted_text = extract_text(file_path)
    detection = pii_detector.detect(extracted_text)
    risk = risk_scoring.score(detection)
    return extracted_text, risk


def _is_owner(doc: DocumentModel, user_id: Optional[int]) -> bool:
    """Open mode (user_id None) sees everything; otherwise only the owner."""
    return user_id is None or doc.user_id == user_id


# ------------------------------------------------------------------ #
# Endpoints                                                             #
# ------------------------------------------------------------------ #
@router.post("/upload", response_model=DocumentScanResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_id: Optional[int] = Depends(get_current_user_id),
) -> DocumentScanResponse:
    """
    Upload a document (PDF, DOCX, TXT), store it securely, record its path,
    size, status and owner in the database, extract text, and run it through the
    privacy scanning pipeline.

    The file is validated (extension, declared MIME type, real content signature,
    size limit) before it is kept; invalid files are never left on disk.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty.")

    # Display name only (the file on disk is named by its random storage key).
    display_name = sanitize_filename(file.filename)[:255]

    # 1. Save file to storage
    storage_key, size_bytes = storage_service.save_file(
        file.file,
        original_filename=file.filename,
        content_type=file.content_type,
    )

    file_path = storage_service.get_file_path(storage_key)
    if not file_path:
        raise HTTPException(status_code=500, detail="Could not locate saved file.")

    # 2. Record path / size / status in the database (status = "uploaded")
    doc_id = _create_document_record(
        filename=display_name,
        storage_key=storage_key,
        file_path=str(file_path),
        size_bytes=size_bytes,
        user_id=user_id,
    )

    # 3. Extract text + scan for PII, tracking the outcome in `status`
    try:
        extracted_text, risk = _process_file(file_path)
    except Exception:
        _set_document_status(doc_id, DOC_STATUS_FAILED)
        raise

    _set_document_status(doc_id, DOC_STATUS_SCANNED)

    return DocumentScanResponse(
        id=doc_id,
        filename=display_name,
        storage_key=storage_key,
        file_path=str(file_path),
        status=DOC_STATUS_SCANNED,
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
async def list_documents(
    status: Optional[str] = Query(
        None, description=f"Filter by status: {', '.join(DOCUMENT_STATUSES)}"
    ),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user_id: Optional[int] = Depends(get_current_user_id),
) -> List[dict]:
    """List stored documents (path, size, status), newest first."""
    if status is not None and status not in DOCUMENT_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Use one of: {', '.join(DOCUMENT_STATUSES)}.",
        )

    if not settings.DATABASE_URL:
        # Fallback if DB is not configured: list files in storage directory
        results = []
        if storage_service.base_path.exists():
            for p in storage_service.base_path.iterdir():
                if p.is_file():
                    results.append({
                        "id": None,
                        "filename": p.name,
                        "storage_key": p.name,
                        "file_path": str(p),
                        "size_bytes": p.stat().st_size,
                        "status": None,
                        "created_at": None,
                        "updated_at": None,
                    })
        return results

    try:
        with get_db_session() as session:
            query = session.query(DocumentModel)
            if status:
                query = query.filter(DocumentModel.status == status)
            if user_id is not None:
                query = query.filter(DocumentModel.user_id == user_id)
            docs = (
                query.order_by(DocumentModel.created_at.desc(), DocumentModel.id.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [d.to_dict() for d in docs]
    except Exception as exc:
        logger.warning("Could not fetch documents from DB: %s", type(exc).__name__)
        return []


@router.get("/{document_id}", response_model=dict)
async def get_document(
    document_id: int,
    user_id: Optional[int] = Depends(get_current_user_id),
) -> dict:
    """Retrieve one document's stored metadata (path, size, status) by id."""
    if not settings.DATABASE_URL:
        raise HTTPException(status_code=503, detail="Database is not configured.")

    try:
        with get_db_session() as session:
            doc = session.get(DocumentModel, document_id)
            if doc is None or not _is_owner(doc, user_id):
                raise HTTPException(status_code=404, detail="Document not found.")
            return doc.to_dict()
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Could not fetch document from DB: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Could not read from database.")


@router.post("/{document_id}/scan", response_model=DocumentScanResponse)
async def scan_stored_document(
    document_id: int,
    user_id: Optional[int] = Depends(get_current_user_id),
) -> DocumentScanResponse:
    """
    Re-run text extraction and PII detection on an already-stored document.

    The file is located from its storage_key (never from the stored path string),
    must be inside the storage folder, and must still match its recorded size.
    """
    if not settings.DATABASE_URL:
        raise HTTPException(status_code=503, detail="Database is not configured.")

    try:
        with get_db_session() as session:
            doc = session.get(DocumentModel, document_id)
            if doc is None or not _is_owner(doc, user_id):
                raise HTTPException(status_code=404, detail="Document not found.")
            record = doc.to_dict()
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Could not fetch document from DB: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Could not read from database.")

    file_path = storage_service.get_secure_path(
        record["storage_key"], expected_size=record["size_bytes"]
    )

    try:
        extracted_text, risk = _process_file(file_path)
    except Exception:
        _set_document_status(document_id, DOC_STATUS_FAILED)
        raise
    _set_document_status(document_id, DOC_STATUS_SCANNED)

    return DocumentScanResponse(
        id=document_id,
        filename=record["filename"] or record["storage_key"],
        storage_key=record["storage_key"],
        file_path=record["file_path"],
        status=DOC_STATUS_SCANNED,
        size_bytes=record["size_bytes"] or file_path.stat().st_size,
        char_count=len(extracted_text),
        text_preview=extracted_text[:400] + ("..." if len(extracted_text) > 400 else ""),
        action=risk.action,
        risk_score=risk.risk_score,
        detected_entities=risk.detected_entities,
        entity_counts=risk.entity_counts,
        raw_text=extracted_text,
    )


@router.delete("/{storage_key}")
async def delete_document(
    storage_key: str,
    user_id: Optional[int] = Depends(get_current_user_id),
):
    """Delete a document by its storage key (owners only when access control is on)."""
    if user_id is not None:
        try:
            with get_db_session() as session:
                owned = (
                    session.query(DocumentModel.id)
                    .filter(
                        DocumentModel.storage_key == storage_key,
                        DocumentModel.user_id == user_id,
                    )
                    .first()
                )
        except Exception as exc:
            logger.warning("Could not verify document owner: %s", type(exc).__name__)
            raise HTTPException(status_code=503, detail="Could not read from database.")
        if owned is None:
            raise HTTPException(status_code=404, detail="Document not found.")

    storage_service.delete_file(storage_key)
    if settings.DATABASE_URL:
        try:
            with get_db_session() as session:
                doc = session.query(DocumentModel).filter(DocumentModel.storage_key == storage_key).first()
                if doc:
                    session.delete(doc)
        except Exception as exc:
            logger.warning("Could not delete document from DB: %s", type(exc).__name__)

    return {"status": "deleted", "storage_key": storage_key}
