"""Sort, filter, and paginate findings for API responses."""
from __future__ import annotations

from typing import List, Optional, Sequence, Set
from urllib.parse import quote, urlencode

from api.schemas.scan_schemas import ScanFindingItemSchema, ScanFindingsPaginationSchema

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
) -> str:
    """Relative path for GET /api/v1/scans/{id}/findings with query params."""
    params: dict[str, str | int] = {}
    if limit is not None:
        params["limit"] = limit
    if offset:
        params["offset"] = offset
    if severity and str(severity).strip():
        params["severity"] = str(severity).strip()
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
        )

    return ScanFindingsPaginationSchema(
        total=total,
        limit=limit,
        offset=offset,
        returned=returned_count,
        has_more=has_more,
        next_path=next_path,
    )
