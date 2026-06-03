#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional


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


def default_ai_normalizer(tool_name: str) -> Callable[[Any], List[Dict[str, Any]]]:
    """
    Generic AI normalizer for all processors.
    Accepts either already-normalized dict findings or tool-specific dicts and
    maps them to a stable shape: {tool,severity,rule_id,path,line,message}.
    """

    severity_keys = (
        "severity",
        "Severity",
        "level",
        "Level",
        "risk",
        "Risk",
        "result",
        "Result",
    )
    rule_id_keys = (
        "rule_id",
        "id",
        "RuleID",
        "ruleId",
        "VulnerabilityID",
        "vulnerability_id",
        "check_id",
        "test",
    )
    path_keys = (
        "path",
        "file",
        "File",
        "filename",
        "file_path",
        "filePath",
        "target",
        "Target",
        "group",
        "package",
        "PkgName",
    )
    line_keys = (
        "line",
        "line_number",
        "StartLine",
        "start",
        "startLine",
        "Start",
    )
    message_keys = (
        "message",
        "Message",
        "description",
        "Description",
        "title",
        "Title",
        "details",
        "Details",
        "advisory",
        "Advisory",
        "test",
    )

    def _norm(findings: Any) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for f in (findings or []):
            if not isinstance(f, dict):
                continue
            sev = str(_first_non_empty(f, severity_keys)).upper()
            rid = str(_first_non_empty(f, rule_id_keys))
            p = str(_first_non_empty(f, path_keys))
            ln = str(_first_non_empty(f, line_keys))
            msg = str(_first_non_empty(f, message_keys))
            out.append(
                {
                    "tool": tool_name,
                    "severity": sev or "UNKNOWN",
                    "rule_id": rid,
                    "path": p,
                    "line": ln,
                    "message": msg,
                }
            )
        return out

    return _norm

