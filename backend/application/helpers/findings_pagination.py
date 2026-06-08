"""Sort, filter, and paginate findings for API responses."""
from __future__ import annotations

import re
from typing import List, Optional, Sequence, Set
from urllib.parse import quote, urlencode

from api.schemas.scan_schemas import ScanFindingItemSchema, ScanFindingsPaginationSchema

MAX_RULE_ID_PATTERN_LEN = 200

SEVERITY_RANK = {
    "CRITICAL": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
    "INFO": 4,
    "UNKNOWN": 5,
}

DEFAULT_FINDINGS_LIMIT = 50
MAX_FINDINGS_LIMIT = 200


def parse_severity_filter(severity: Optional[str]) -> Optional[Set[str]]:
    """Parse comma-separated severity list (e.g. CRITICAL,HIGH)."""
    if not severity or not str(severity).strip():
        return None
    parts = {p.strip().upper() for p in str(severity).split(",") if p.strip()}
    return parts or None


def severity_rank(severity: str) -> int:
    key = (severity or "").upper().strip()
    return SEVERITY_RANK.get(key, SEVERITY_RANK["UNKNOWN"])


def sort_findings(items: List[ScanFindingItemSchema]) -> List[ScanFindingItemSchema]:
    """Stable order: severity (desc), path, rule_id, line, message."""
    return sorted(
        items,
        key=lambda f: (
            severity_rank(f.severity),
            (f.path or "").lower(),
            (f.rule_id or "").lower(),
            str(f.line or ""),
            (f.message or "").lower(),
        ),
    )


def filter_findings_by_severity(
    items: Sequence[ScanFindingItemSchema],
    severities: Optional[Set[str]],
) -> List[ScanFindingItemSchema]:
    if not severities:
        return list(items)
    return [
        f for f in items if (f.severity or "").upper().strip() in severities
    ]


def _compile_rule_id_pattern(rule_id: Optional[str]) -> Optional[re.Pattern[str]]:
    raw = (rule_id or "").strip()
    if not raw:
        return None
    if len(raw) > MAX_RULE_ID_PATTERN_LEN:
        raw = raw[:MAX_RULE_ID_PATTERN_LEN]
    try:
        return re.compile(raw, re.IGNORECASE)
    except re.error:
        escaped = re.escape(raw)
        return re.compile(f"^{escaped}$", re.IGNORECASE)


def filter_findings_by_tool(
    items: Sequence[ScanFindingItemSchema],
    tool: Optional[str],
) -> List[ScanFindingItemSchema]:
    needle = (tool or "").strip().lower()
    if not needle:
        return list(items)
    return [f for f in items if (f.tool or "").strip().lower() == needle]


def filter_findings_by_path_prefix(
    items: Sequence[ScanFindingItemSchema],
    path_prefix: Optional[str],
) -> List[ScanFindingItemSchema]:
    prefix = (path_prefix or "").strip()
    if not prefix:
        return list(items)
    prefix_lower = prefix.lower()
    return [
        f for f in items
        if (f.path or "").lower().startswith(prefix_lower)
    ]


def filter_findings_by_rule_id(
    items: Sequence[ScanFindingItemSchema],
    rule_id: Optional[str],
) -> List[ScanFindingItemSchema]:
    pattern = _compile_rule_id_pattern(rule_id)
    if pattern is None:
        return list(items)
    return [
        f for f in items
        if pattern.search((f.rule_id or "").strip())
    ]


def apply_findings_filters(
    items: Sequence[ScanFindingItemSchema],
    *,
    severities: Optional[Set[str]] = None,
    tool: Optional[str] = None,
    path_prefix: Optional[str] = None,
    rule_id: Optional[str] = None,
) -> List[ScanFindingItemSchema]:
    """Apply severity, tool, path_prefix, and rule_id filters in stable order."""
    out = filter_findings_by_severity(items, severities)
    out = filter_findings_by_tool(out, tool)
    out = filter_findings_by_path_prefix(out, path_prefix)
    out = filter_findings_by_rule_id(out, rule_id)
    return out


def findings_filters_active(
    *,
    severities: Optional[Set[str]] = None,
    tool: Optional[str] = None,
    path_prefix: Optional[str] = None,
    rule_id: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> bool:
    return bool(
        severities
        or (tool or "").strip()
        or (path_prefix or "").strip()
        or (rule_id or "").strip()
        or limit is not None
        or offset > 0
    )


def paginate_findings(
    items: Sequence[ScanFindingItemSchema],
    *,
    limit: Optional[int],
    offset: int = 0,
) -> List[ScanFindingItemSchema]:
    start = max(0, offset)
    if limit is None:
        return list(items)[start:]
    end = start + max(0, limit)
    return list(items)[start:end]


def build_findings_poll_path(
    scan_id: str,
    *,
    limit: Optional[int] = None,
    offset: int = 0,
    severity: Optional[str] = None,
    tool: Optional[str] = None,
    path_prefix: Optional[str] = None,
    rule_id: Optional[str] = None,
) -> str:
    """Relative path for GET /api/v1/scans/{id}/findings with query params."""
    params: dict[str, str | int] = {}
    if limit is not None:
        params["limit"] = limit
    if offset:
        params["offset"] = offset
    if severity and str(severity).strip():
        params["severity"] = str(severity).strip()
    if tool and str(tool).strip():
        params["tool"] = str(tool).strip()
    if path_prefix and str(path_prefix).strip():
        params["path_prefix"] = str(path_prefix).strip()
    if rule_id and str(rule_id).strip():
        params["rule_id"] = str(rule_id).strip()
    base = f"/api/v1/scans/{scan_id}/findings"
    if not params:
        return base
    return f"{base}?{urlencode(params, quote_via=quote)}"


def build_pagination_meta(
    *,
    scan_id: str,
    total: int,
    limit: Optional[int],
    offset: int,
    returned_count: int,
    severity: Optional[str] = None,
    tool: Optional[str] = None,
    path_prefix: Optional[str] = None,
    rule_id: Optional[str] = None,
) -> ScanFindingsPaginationSchema:
    if limit is not None:
        has_more = offset + returned_count < total
        next_offset = offset + limit if has_more else None
    else:
        has_more = offset + returned_count < total
        next_offset = offset + returned_count if has_more else None

    next_path: Optional[str] = None
    if has_more and next_offset is not None:
        next_path = build_findings_poll_path(
            scan_id,
            limit=limit,
            offset=next_offset,
            severity=severity,
            tool=tool,
            path_prefix=path_prefix,
            rule_id=rule_id,
        )

    return ScanFindingsPaginationSchema(
        total=total,
        limit=limit,
        offset=offset,
        returned=returned_count,
        has_more=has_more,
        next_path=next_path,
    )
