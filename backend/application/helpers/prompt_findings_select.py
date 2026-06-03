"""Select and sort findings for AI prompt generation (shared with report table semantics)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

SEV_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
MIN_SEVERITY_THRESHOLD = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4, "ALL": 99}


def normalize_severity(sev: Any) -> str:
    raw = str(sev or "").strip().upper()
    if not raw:
        return "INFO"
    if "CRIT" in raw:
        return "CRITICAL"
    if raw in ("HIGH", "ERROR"):
        return "HIGH"
    if raw in ("MEDIUM", "MED", "WARN", "MODERATE"):
        return "MEDIUM"
    if raw == "LOW":
        return "LOW"
    if raw in ("INFO", "INFORMATIONAL", "NOTE"):
        return "INFO"
    return raw


def severity_rank(sev: Any) -> int:
    return SEV_ORDER.get(normalize_severity(sev), 5)


def passes_min_severity(sev: Any, min_severity: str) -> bool:
    key = (min_severity or "ALL").strip().upper()
    if key == "ALL":
        return True
    threshold = MIN_SEVERITY_THRESHOLD.get(key, 1)
    return severity_rank(sev) <= threshold


def count_by_severity(findings: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {k: 0 for k in SEV_ORDER}
    for f in findings:
        key = normalize_severity(f.get("severity"))
        counts[key] = counts.get(key, 0) + 1
    return counts


def sort_findings(findings: List[Dict[str, Any]], sort_by: str) -> List[Dict[str, Any]]:
    key = (sort_by or "severity").strip().lower()

    def _path(f: Dict[str, Any]) -> str:
        return str(f.get("path") or "").lower()

    def _tool(f: Dict[str, Any]) -> str:
        return str(f.get("tool") or "").lower()

    if key == "tool":
        return sorted(
            findings,
            key=lambda f: (_tool(f), severity_rank(f.get("severity")), _path(f)),
        )
    if key == "path":
        return sorted(
            findings,
            key=lambda f: (_path(f), severity_rank(f.get("severity")), _tool(f)),
        )
    return sorted(
        findings,
        key=lambda f: (severity_rank(f.get("severity")), _tool(f), _path(f)),
    )


def select_findings_for_prompt(
    findings: List[Dict[str, Any]],
    *,
    max_findings: int = 100,
    min_severity: str = "HIGH",
    tool: Optional[str] = None,
    sort_by: str = "severity",
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Filter by tool/min severity, sort, then cap count. Returns (selected, meta)."""
    total = len(findings or [])
    tool_key = (tool or "").strip()
    filtered: List[Dict[str, Any]] = []
    for f in findings or []:
        if not isinstance(f, dict):
            continue
        if tool_key and str(f.get("tool") or "").strip() != tool_key:
            continue
        if not passes_min_severity(f.get("severity"), min_severity):
            continue
        filtered.append(f)

    sorted_list = sort_findings(filtered, sort_by)
    cap = max(1, int(max_findings))
    selected = sorted_list[:cap]
    meta = {
        "total": total,
        "matched": len(filtered),
        "included": len(selected),
        "min_severity": (min_severity or "HIGH").upper(),
        "tool": tool_key or None,
        "sort_by": sort_by or "severity",
        "matched_by_severity": count_by_severity(filtered),
        "included_by_severity": count_by_severity(selected),
    }
    return selected, meta
