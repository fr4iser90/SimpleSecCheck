"""Load scan findings from results/summary/findings.json (or HTML fallback)."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config.settings import get_settings


def findings_json_path(scan_id: str) -> Path:
    s = get_settings()
    base = Path(s.RESULTS_DIR_HOST if hasattr(s, "RESULTS_DIR_HOST") else "/app/results")
    return base / scan_id / "summary" / "findings.json"


def _extract_findings_from_report_html(html_path: Path) -> List[Dict[str, Any]]:
    try:
        text = html_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    match = re.search(
        r'<script[^>]*\sid="findings-data"[^>]*>\s*([\s\S]*?)\s*</script>',
        text,
    )
    if not match:
        return []
    raw = match.group(1).strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    return data if isinstance(data, list) else []


def load_findings_payload(scan_id: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Load findings document for a scan.

    Returns (payload, source) where source is 'file', 'html', or 'missing'.
    payload keys: generated_at, findings, summary (summary optional).
    """
    path = findings_json_path(scan_id)
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = None
        if isinstance(data, dict) and isinstance(data.get("findings"), list):
            return data, "file"
        if isinstance(data, list):
            return {
                "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "findings": data,
                "summary": {},
            }, "file"

    html_path = path.parent / "summary.html"
    if html_path.is_file():
        findings = _extract_findings_from_report_html(html_path)
        if findings:
            return {
                "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "findings": findings,
                "summary": {},
            }, "html"

    return None, "missing"
