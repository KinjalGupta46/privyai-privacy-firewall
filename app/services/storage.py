"""
app/services/storage.py

Storage service adapter for PrivyAI.
Handles secure file storage, storage key generation, and file retrieval.
Default implementation supports local disk storage in LOCAL_STORAGE_PATH (e.g. tmp_uploads/).
"""

from __future__ import annotations

import os
import uuid
import shutil
from pathlib import Path
from typing import BinaryIO, Optional

from app.core.config import settings
from app.utils.exceptions import FileTooLargeError, UnsupportedFileTypeError


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}


class StorageService:
    """Manages document file storage on disk or object store."""

    def __init__(self, base_path: Optional[str] = None) -> None:
        self.base_path = Path(base_path or settings.LOCAL_STORAGE_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)

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


# Singleton storage service instance
storage_service = StorageService()
