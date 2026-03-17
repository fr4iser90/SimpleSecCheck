"""
Upload Service

Handles ZIP upload: validation, optional ClamAV scan, safe extraction with limits.
Stores extracted content under UPLOAD_STORAGE_PATH / upload_id for worker mount.
"""
import logging
import os
import shutil
import zipfile
from pathlib import Path
from typing import Optional
import uuid

from config.settings import get_settings
from infrastructure.services.clamav_service import scan_file, is_clamav_available

logger = logging.getLogger(__name__)


class UploadRejectedError(Exception):
    """Raised when an upload is rejected (size, virus, path traversal, etc.)."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _normalize_upload_id(target_url: str) -> str:
    """Extract raw upload_id from target_url (may be UUID or 'upload:<id>')."""
    s = target_url.strip()
    if s.startswith("upload:"):
        return s[7:].strip()
    return s


def get_upload_path(upload_id: str) -> Path:
    """Return the absolute path where an upload is stored (does not check existence)."""
    if not upload_id or not upload_id.strip():
        raise ValueError("Invalid upload_id")
    # Only allow UUID-like segment (alphanumeric + hyphen)
    safe_id = upload_id.strip()
    if ".." in safe_id or "/" in safe_id or "\\" in safe_id:
        raise ValueError("Invalid upload_id")
    if not all(c.isalnum() or c == "-" for c in safe_id):
        raise ValueError("Invalid upload_id")
    settings = get_settings()
    base = Path(settings.UPLOAD_STORAGE_PATH)
    return (base / safe_id).resolve()


def resolve_upload_mount_path(upload_id: str) -> Optional[str]:
    """
    Resolve upload_id to the directory path the worker should mount.
    Returns None if upload does not exist.
    """
    try:
        uid = _normalize_upload_id(upload_id)
        path = get_upload_path(uid)
        if path.is_dir():
            return str(path)
        return None
    except (ValueError, Exception):
        return None


def store_upload(zip_path: str | Path, user_id: Optional[str] = None) -> str:
    """
    Validate ZIP, optionally virus-scan, extract with limits, return upload_id.

    Args:
        zip_path: Path to the uploaded ZIP file (temporary file).
        user_id: Optional user id for logging.

    Returns:
        upload_id (UUID string) - use as target_url for scan with target_type=uploaded_code.

    Raises:
        UploadRejectedError: If file too large, virus found, or extraction limits exceeded.
    """
    settings = get_settings()
    zip_path = Path(zip_path).resolve()
    if not zip_path.is_file():
        raise UploadRejectedError("Uploaded file not found")

    # Size limit
    size = zip_path.stat().st_size
    if size > settings.ZIP_UPLOAD_MAX_BYTES:
        raise UploadRejectedError(
            f"ZIP too large: {size} bytes (max {settings.ZIP_UPLOAD_MAX_BYTES})"
        )

    # Virus scan (before extract)
    if settings.ZIP_UPLOAD_VIRUS_SCAN_ENABLED:
        if not is_clamav_available():
            raise UploadRejectedError(
                "Virus scan is enabled but ClamAV is not installed (clamscan/clamdscan not found). "
                "Install ClamAV or set ZIP_UPLOAD_VIRUS_SCAN_ENABLED=false."
            )
        ok, msg = scan_file(zip_path)
        if not ok:
            raise UploadRejectedError(f"Virus scan failed: {msg}")

    upload_id = str(uuid.uuid4())
    extract_dir = get_upload_path(upload_id)
    extract_dir.mkdir(parents=True, exist_ok=True)
    max_bytes = settings.ZIP_UPLOAD_MAX_UNCOMPRESSED_BYTES
    max_files = settings.ZIP_UPLOAD_MAX_FILES
    try:
        _safe_extract_zip(zip_path, extract_dir, max_bytes, max_files)
    except UploadRejectedError:
        shutil.rmtree(extract_dir, ignore_errors=True)
        raise
    except Exception as e:
        shutil.rmtree(extract_dir, ignore_errors=True)
        logger.exception("ZIP extraction failed")
        raise UploadRejectedError(f"Extraction failed: {e}") from e

    logger.info("Upload stored upload_id=%s user_id=%s", upload_id, user_id)
    return upload_id


def _safe_extract_zip(
    zip_path: Path, extract_dir: Path, max_uncompressed_bytes: int, max_files: int
) -> None:
    """
    Extract ZIP with path-traversal protection and limits.
    Raises UploadRejectedError if limits exceeded or unsafe paths.
    """
    extract_dir_resolved = extract_dir.resolve()
    total_size = 0
    file_count = 0

    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            file_count += 1
            if file_count > max_files:
                raise UploadRejectedError(
                    f"Too many files in ZIP (max {max_files})"
                )

            # Reject path traversal and absolute paths
            name = info.filename
            if ".." in name or name.startswith("/") or (os.path.sep == "\\" and name.startswith("\\")):
                raise UploadRejectedError(f"Unsafe path in ZIP: {name}")

            # Resolve path and ensure it stays under extract_dir
            target = (extract_dir / name).resolve()
            if not str(target).startswith(str(extract_dir_resolved)):
                raise UploadRejectedError(f"Path traversal in ZIP: {name}")

            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as dst:
                chunk_size = 1024 * 1024
                while True:
                    chunk = src.read(chunk_size)
                    if not chunk:
                        break
                    total_size += len(chunk)
                    if total_size > max_uncompressed_bytes:
                        raise UploadRejectedError(
                            f"Uncompressed size limit exceeded (max {max_uncompressed_bytes} bytes)"
                        )
                    dst.write(chunk)
