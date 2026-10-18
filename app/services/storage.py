"""
app/services/storage.py

Storage service adapter for PrivyAI.
Handles secure file storage, storage key generation, and file retrieval.
Default implementation supports local disk storage in LOCAL_STORAGE_PATH (e.g. tmp_uploads/).
"""

from __future__ import annotations

import os
import re
import uuid
import shutil
import zipfile
from pathlib import Path
from typing import BinaryIO, Optional

from app.core.config import settings
from app.utils.exceptions import (
    FileTooLargeError,
    PrivyAIError,
    UnsupportedFileTypeError,
    ValidationError,
)


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}

# Browsers often label unknown/Office files as a generic binary type.
_GENERIC_MIME_TYPES = {"application/octet-stream", "binary/octet-stream"}

# Keys we generate look exactly like this (uuid4 hex + allowed extension).
_STORAGE_KEY_RE = re.compile(r"^[0-9a-f]{32}\.(pdf|docx|txt)$")

# DOCX is a ZIP: guard against zip bombs before a parser opens it.
_MAX_DOCX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
_MAX_DOCX_ENTRIES = 5000


class StorageService:
    """Manages document file storage on disk or object store."""

    def __init__(self, base_path: Optional[str] = None) -> None:
        self.base_path = Path(base_path or settings.LOCAL_STORAGE_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._restrict_permissions(self.base_path, directory=True)

    def save_file(
        self,
        file_obj: BinaryIO,
        original_filename: str,
        content_type: Optional[str] = None,
    ) -> tuple[str, int]:
        """
        Validate, generate a secure storage key, and save the file.

        Returns:
            tuple[storage_key, file_size_in_bytes]
        """
        # Validate extension
        suffix = Path(original_filename).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise UnsupportedFileTypeError(content_type or suffix)
        self._check_declared_mime(content_type)

        # Unique UUID-based storage key (never store original sensitive filename on disk)
        storage_key = f"{uuid.uuid4().hex}{suffix}"
        target_path = self.base_path / storage_key

        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        file_size = 0

        with open(target_path, "wb") as buffer:
            while chunk := file_obj.read(1024 * 64):
                file_size += len(chunk)
                if file_size > max_bytes:
                    # Clean up partial file on error
                    buffer.close()
                    target_path.unlink(missing_ok=True)
                    raise FileTooLargeError(settings.MAX_UPLOAD_SIZE_MB)
                buffer.write(chunk)

        # Reject empty / mislabelled / malformed files; never keep them on disk.
        try:
            if file_size == 0:
                raise ValidationError("Uploaded file is empty.")
            self._validate_content(target_path, suffix)
        except Exception:
            target_path.unlink(missing_ok=True)
            raise
        self._restrict_permissions(target_path)

        return storage_key, file_size

    def get_file_path(self, storage_key: str) -> Optional[Path]:
        """Return the absolute path of the stored file if it exists."""
        # Sanitize against path traversal
        clean_key = Path(storage_key).name
        target = self.base_path / clean_key
        return target if target.exists() else None

    def delete_file(self, storage_key: str) -> bool:
        """Delete stored file from storage."""
        clean_key = Path(storage_key).name
        target = self.base_path / clean_key
        if target.exists():
            target.unlink()
            return True
        return False

    def get_secure_path(self, storage_key: str, expected_size: Optional[int] = None) -> Path:
        """
        Return the path of a stored file for processing (text extraction / PII scan).

        Stricter than get_file_path(): the key must match the exact format this
        service generates, the file must live directly inside the storage folder,
        must not be a symlink, and (when given) must still have the size recorded
        in the database. Raises PrivyAIError (404 / 409) instead of returning None.
        """
        if not _STORAGE_KEY_RE.match(storage_key or ""):
            raise PrivyAIError("Stored file not found.", status_code=404)

        target = self.base_path / storage_key
        if target.is_symlink() or not target.is_file():
            raise PrivyAIError("Stored file not found.", status_code=404)
        if target.resolve().parent != self.base_path.resolve():
            raise PrivyAIError("Stored file not found.", status_code=404)
        if expected_size is not None and target.stat().st_size != expected_size:
            raise PrivyAIError(
                "Stored file failed its integrity check (size mismatch).",
                status_code=409,
            )
        return target

    # ------------------------------------------------------------------ #
    # Validation / hardening helpers                                       #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _check_declared_mime(content_type: Optional[str]) -> None:
        """Reject uploads whose declared MIME type is clearly not a document."""
        if not content_type:
            return
        base = content_type.split(";")[0].strip().lower()
        if base in ALLOWED_MIME_TYPES or base in _GENERIC_MIME_TYPES:
            return
        raise UnsupportedFileTypeError(base)

    @staticmethod
    def _validate_content(path: Path, suffix: str) -> None:
        """Check the real file content matches its extension (not just the name)."""
        if suffix == ".pdf":
            with open(path, "rb") as fh:
                if fh.read(5) != b"%PDF-":
                    raise ValidationError("File content is not a valid PDF.")
        elif suffix == ".docx":
            try:
                with zipfile.ZipFile(path) as zf:
                    infos = zf.infolist()
                    names = {i.filename for i in infos}
                    if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                        raise ValidationError("File content is not a valid DOCX document.")
                    if len(infos) > _MAX_DOCX_ENTRIES or (
                        sum(i.file_size for i in infos) > _MAX_DOCX_UNCOMPRESSED_BYTES
                    ):
                        raise ValidationError("DOCX document is too complex to process safely.")
            except zipfile.BadZipFile:
                raise ValidationError("File content is not a valid DOCX document.")
        elif suffix == ".txt":
            with open(path, "rb") as fh:
                if b"\x00" in fh.read(8192):
                    raise ValidationError("File content is not valid plain text.")

    @staticmethod
    def _restrict_permissions(path: Path, directory: bool = False) -> None:
        """Owner-only access (0700 dirs / 0600 files). Best effort; no-op on Windows."""
        try:
            os.chmod(path, 0o700 if directory else 0o600)
        except OSError:
            pass


# Singleton storage service instance
storage_service = StorageService()
