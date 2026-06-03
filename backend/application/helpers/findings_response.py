"""Build API findings response from stored payload and scan DTO."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from api.schemas.scan_schemas import (
    ScanFindingItemSchema,
    ScanFindingsResponseSchema,
    ScanFindingsSummarySchema,
)
from application.dtos.scan_dto import ScanDTO
from application.helpers.findings_file import load_findings_payload
from application.helpers.findings_pagination import (
    build_pagination_meta,
    filter_findings_by_severity,
    paginate_findings,
    parse_severity_filter,
    sort_findings,
)


def finding_item_from_dict(raw: Dict[str, Any]) -> ScanFindingItemSchema:
    from scanner.output.ai_normalizer_utils import normalize_finding_fields

    fields = normalize_finding_fields(raw) if isinstance(raw, dict) else {}
    cwe = raw.get("cwe") or raw.get("CWE") or raw.get("cwe_id")
    fix_hint = raw.get("fix_hint") or raw.get("remediation") or raw.get("fix")
    policy_key = str(raw.get("policy_key") or "").strip()
    if not policy_key:
        try:
            from scanner.core.policy_schema_registry import display_name_to_policy_key

            tool_name = str(raw.get("tool") or "").strip()
            policy_key = display_name_to_policy_key().get(tool_name, "")
        except ImportError:
            policy_key = ""

    return ScanFindingItemSchema(
        tool=str(raw.get("tool") or ""),
        policy_key=policy_key,
        severity=str(raw.get("severity") or fields.get("severity") or ""),
        path=str(fields.get("path") or raw.get("path") or raw.get("file") or ""),
        line=str(fields.get("line") or raw.get("line") or raw.get("line_number") or ""),
        message=str(fields.get("message") or raw.get("message") or ""),
        rule_id=str(fields.get("rule_id") or raw.get("rule_id") or raw.get("check_id") or ""),
        cwe=str(cwe) if cwe else None,
        fix_hint=str(fix_hint) if fix_hint else None,
    )


def summary_from_payload_or_scan(
    payload_summary: Optional[Dict[str, Any]],
    scan_dto: ScanDTO,
) -> ScanFindingsSummarySchema:
    if isinstance(payload_summary, dict) and payload_summary:
        return ScanFindingsSummarySchema(
            total_vulnerabilities=int(payload_summary.get("total_vulnerabilities", 0) or 0),
            critical_vulnerabilities=int(payload_summary.get("critical_vulnerabilities", 0) or 0),
            high_vulnerabilities=int(payload_summary.get("high_vulnerabilities", 0) or 0),
            medium_vulnerabilities=int(payload_summary.get("medium_vulnerabilities", 0) or 0),
            low_vulnerabilities=int(payload_summary.get("low_vulnerabilities", 0) or 0),
            info_vulnerabilities=int(payload_summary.get("info_vulnerabilities", 0) or 0),
        )
    return ScanFindingsSummarySchema(
        total_vulnerabilities=scan_dto.total_vulnerabilities or 0,
        critical_vulnerabilities=scan_dto.critical_vulnerabilities or 0,
        high_vulnerabilities=scan_dto.high_vulnerabilities or 0,
        medium_vulnerabilities=scan_dto.medium_vulnerabilities or 0,
        low_vulnerabilities=scan_dto.low_vulnerabilities or 0,
        info_vulnerabilities=scan_dto.info_vulnerabilities or 0,
    )


def build_findings_response(
    scan_id: str,
    scan_dto: ScanDTO,
    *,
    status_str: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    severity: Optional[str] = None,
) -> Optional[ScanFindingsResponseSchema]:
    """Return findings response if report data exists; else None."""
    payload, source = load_findings_payload(scan_id)
    if payload is None:
        return None

    status = status_str or (
        scan_dto.status.value
        if hasattr(scan_dto.status, "value")
        else str(scan_dto.status or "")
    )
    raw_findings = payload.get("findings") if isinstance(payload, dict) else []
    if not isinstance(raw_findings, list):
        raw_findings = []

    items = [
        finding_item_from_dict(f) for f in raw_findings if isinstance(f, dict)
    ]
    items = sort_findings(items)

    severity_set = parse_severity_filter(severity)
    filtered = filter_findings_by_severity(items, severity_set)
    total = len(filtered)
    page = paginate_findings(filtered, limit=limit, offset=offset)

    generated_at = payload.get("generated_at") if isinstance(payload, dict) else None

    use_pagination = limit is not None or offset > 0 or severity_set is not None
    pagination = None
    if use_pagination:
        pagination = build_pagination_meta(
            scan_id=scan_id,
            total=total,
            limit=limit,
            offset=offset,
            returned_count=len(page),
            severity=severity,
        )

    return ScanFindingsResponseSchema(
        scan_id=scan_id,
        status=str(status).lower(),
        generated_at=str(generated_at) if generated_at else None,
        findings=page,
        summary=summary_from_payload_or_scan(
            payload.get("summary") if isinstance(payload, dict) else None,
            scan_dto,
        ),
        pagination=pagination,
        source=source,
    )
