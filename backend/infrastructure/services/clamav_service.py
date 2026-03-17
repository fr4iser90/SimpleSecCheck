"""
ClamAV Service

Scans files for malware using clamscan (subprocess).
Used by the upload API before accepting ZIP uploads when ZIP_UPLOAD_VIRUS_SCAN_ENABLED is True.
"""
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)

# Default clamscan executable name (may be clamdscan if daemon is used)
CLAMSCAN_CMD = "clamscan"


def is_clamav_available() -> bool:
    """Return True if clamscan (or clamdscan) is available on PATH."""
    return bool(shutil.which(CLAMSCAN_CMD)) or bool(shutil.which("clamdscan"))


def scan_file(file_path: str | Path) -> Tuple[bool, str]:
    """
    Scan a single file with ClamAV.

    Args:
        file_path: Absolute path to the file to scan.

    Returns:
        (is_clean, message). is_clean True if no virus found or scan skipped; False if infected or error.
    """
    path = Path(file_path).resolve()
    if not path.is_file():
        return False, "File not found"

    cmd = shutil.which(CLAMSCAN_CMD) or shutil.which("clamdscan")
    if not cmd:
        return False, "ClamAV not installed (clamscan/clamdscan not found)"

    try:
        # clamscan exit: 0 = clean, 1 = infected, 2 = error
        result = subprocess.run(
            [cmd, "--no-summary", str(path)],
            capture_output=True,
            timeout=120,
            text=True,
        )
        if result.returncode == 0:
            return True, "OK"
        if result.returncode == 1:
            out = (result.stdout or "") + (result.stderr or "")
            return False, f"Threat detected: {out.strip() or 'infected'}"
        return False, result.stderr.strip() or f"clamscan exited with {result.returncode}"
    except subprocess.TimeoutExpired:
        return False, "Scan timed out"
    except Exception as e:
        logger.exception("ClamAV scan failed")
        return False, str(e)
