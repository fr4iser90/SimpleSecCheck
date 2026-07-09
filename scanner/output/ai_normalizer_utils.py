#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from shared.finding_normalize import normalize_finding_fields

__all__ = ["normalize_finding_fields", "format_rule_message_cell", "default_ai_normalizer"]


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

