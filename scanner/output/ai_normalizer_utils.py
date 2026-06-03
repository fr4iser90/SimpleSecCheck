#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

_SEVERITY_KEYS: Tuple[str, ...] = (
    "severity",
    "Severity",
    "level",
    "Level",
    "risk",
    "Risk",
    "result",
    "Result",
)
_RULE_ID_KEYS: Tuple[str, ...] = (
    "rule_id",
    "id",
    "RuleID",
    "ruleId",
    "VulnerabilityID",
    "vulnerability_id",
    "check_id",
    "test_id",
    "test",
    "CVE",
    "name",
    "package",
    "template_id",
    "detector",
    "warning_type",
)
_PATH_KEYS: Tuple[str, ...] = (
    "path",
    "file",
    "File",
    "filename",
    "file_path",
    "filePath",
    "target",
    "Target",
    "group",
    "dependency_path",
    "Dependency",
    "fileName",
    "package",
    "PkgName",
)
_LINE_KEYS: Tuple[str, ...] = (
    "line",
    "line_number",
    "StartLine",
    "start",
    "startLine",
    "Start",
)
_MESSAGE_KEYS: Tuple[str, ...] = (
    "message",
    "Message",
    "title",
    "Title",
    "description",
    "Description",
    "details",
    "Details",
    "advisory",
    "Advisory",
    "test",
    "issue_text",
)


def _first_non_empty(d: Dict[str, Any], keys: Iterable[str]) -> Any:
    for k in keys:
        if k in d:
            v = d.get(k)
            if v is None:
                continue
            s = str(v)
            if s != "":
                return v
    return ""


def _format_via(via: Any) -> str:
    if via is None:
        return ""
    if isinstance(via, str):
        return via.strip()
    if isinstance(via, list):
        parts = []
        for item in via:
            if isinstance(item, str) and item.strip():
                parts.append(item.strip())
            elif isinstance(item, dict):
                parts.append(
                    str(item.get("title") or item.get("name") or item.get("source") or item).strip()
                )
        return "; ".join(p for p in parts if p)
    return str(via).strip()


def normalize_finding_fields(finding: Dict[str, Any]) -> Dict[str, str]:
    """Map processor-specific finding dicts to report/API row fields."""
    sev = str(_first_non_empty(finding, _SEVERITY_KEYS)).upper()
    rule_id = str(_first_non_empty(finding, _RULE_ID_KEYS))
    path = str(_first_non_empty(finding, _PATH_KEYS))
    line = _first_non_empty(finding, _LINE_KEYS)
    if line is None and isinstance(finding.get("start"), dict):
        line = finding["start"].get("line", "")
    line_s = str(line) if line is not None else ""
    message = str(_first_non_empty(finding, _MESSAGE_KEYS))
    if not message:
        via = _format_via(finding.get("via"))
        if via:
            message = via
    if not message and finding.get("range"):
        message = f"Affected range: {finding.get('range')}"
    if rule_id.lower() == "none":
        rule_id = ""
    return {
        "severity": sev,
        "rule_id": rule_id,
        "path": path,
        "line": line_s,
        "message": message,
    }


def format_rule_message_cell(rule_id: str, message: str) -> str:
    """HTML table cell: rule + message without a lone colon when rule_id is empty."""
    rid = (rule_id or "").strip()
    msg = (message or "").strip()
    if rid and msg:
        return f"{rid}: {msg}"
    return rid or msg


def default_ai_normalizer(
    tool_name: str,
    *,
    policy_key: Optional[str] = None,
    policy_spec: Optional[Any] = None,
) -> Callable[[Any], List[Dict[str, Any]]]:
    """
    Generic AI normalizer for all processors.
    Accepts either already-normalized dict findings or tool-specific dicts and
    maps them to a stable shape: {tool, policy_key, severity, rule_id, path, line, message, policy_match?}.
    """

    def _norm(findings: Any) -> List[Dict[str, Any]]:
        from scanner.core.policy_schema_registry import policy_match_values_from_finding

        out: List[Dict[str, Any]] = []
        for f in (findings or []):
            if not isinstance(f, dict):
                continue
            fields = normalize_finding_fields(f)
            entry: Dict[str, Any] = {
                "tool": tool_name,
                "policy_key": policy_key or "",
                "severity": fields["severity"] or "UNKNOWN",
                "rule_id": fields["rule_id"],
                "path": fields["path"],
                "line": fields["line"],
                "message": fields["message"],
            }
            if policy_spec is not None and policy_key:
                entry["policy_match"] = policy_match_values_from_finding(f, policy_spec)
            out.append(entry)
        return out

    return _norm

