"""
app/services/document_parser.py

Text extraction service for PDF, DOCX, and TXT files.
Extracts clean, readable text from uploaded files to prepare them for
privacy scanning and LLM reasoning.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from app.utils.exceptions import PrivyAIError

logger = logging.getLogger(__name__)


class DocumentParsingError(PrivyAIError):
    """Raised when parsing or text extraction fails."""

    def __init__(self, detail: str = "Failed to extract text from document.") -> None:
        super().__init__(detail, status_code=422)


def extract_text(file_path: Path | str) -> str:
    """
    Extract text content from a PDF, DOCX, or plain text file.

    Args:
        file_path: Path to the target file.

    Returns:
        Extracted plain text.
    """
    path = Path(file_path)
    if not path.exists():
        raise DocumentParsingError("File not found on storage.")

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return _extract_from_pdf(path)
    elif suffix == ".docx":
        return _extract_from_docx(path)
    elif suffix == ".txt":
        return _extract_from_txt(path)
    else:
        raise DocumentParsingError(f"Unsupported format '{suffix}' for text extraction.")


def _extract_from_pdf(path: Path) -> str:
    try:
        import fitz  # PyMuPDF

        text_parts = []
        with fitz.open(str(path)) as doc:
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    text_parts.append(text.strip())

        return "\n\n".join(text_parts)
    except Exception as exc:
        logger.error("Error reading PDF: %s", type(exc).__name__)
        raise DocumentParsingError(f"Could not parse PDF document: {exc}")


def _extract_from_docx(path: Path) -> str:
    try:
        import docx

        doc = docx.Document(str(path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    except Exception as exc:
        logger.error("Error reading DOCX: %s", type(exc).__name__)
        raise DocumentParsingError(f"Could not parse DOCX document: {exc}")


def _extract_from_txt(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1", errors="replace")
    except Exception as exc:
        raise DocumentParsingError(f"Could not read text file: {exc}")
