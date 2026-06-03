#!/usr/bin/env python3
"""
Finding policy schema — derived from scanner plugin processors (policy_key + ToolPolicySpec).

Single source of truth for API schema, AI prompts, and policy validation.
"""
from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from scanner.core.policy_engine import ToolPolicySpec
from scanner.output.processor_registry import ReportProcessor

# Deprecated top-level keys → canonical policy_key
POLICY_KEY_ALIASES: Dict[str, str] = {
    "owasp_dependency_check": "owasp_dc",
    "owasp-dependency-check": "owasp_dc",
    "dependency-check": "owasp_dc",
}

_FIELD_REASON = {
    "type": "string",
    "required": True,
    "description": "Human-readable justification (shown in report accepted-findings section).",
}

_FIELD_NEW_SEVERITY = {
    "type": "string",
    "required": True,
    "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"],
    "description": "Severity to assign when override matches.",
}

_DEDUPE_SEMGREP = {
    "type": "object",
    "fields": {
        "enabled": {
            "type": "boolean",
            "required": False,
            "default": True,
            "description": "Enable line-window deduplication for Semgrep findings.",
        },
        "line_window": {
            "type": "integer",
            "required": False,
            "default": 2,
            "description": "Merge findings on same rule+path within this many lines.",
        },
        "line_field": {
            "type": "string",
            "required": False,
            "description": "Finding line field for dedupe (default: start).",
        },
        "group_fields": {
            "type": "array",
            "required": False,
            "description": "Fields that define a dedupe group (default: rule_id, path, message, severity).",
        },
    },
}


@dataclass(frozen=True)
class PolicyToolMeta:
    policy_key: str
    display_names: Tuple[str, ...]
    policy_spec: ToolPolicySpec
    policy_example_snippet: Optional[str] = None
    extra_block_properties: Optional[Tuple[str, ...]] = None  # e.g. severity_overrides, dedupe


def _field_rule_id_spec(mode: str) -> Dict[str, Any]:
    desc = (
        "Rule/check ID as regex matched against finding rule_id (CodeQL and similar)."
        if mode == "regex"
        else "Rule/check ID; omitted matches any. Compared for exact equality."
    )
    return {"type": "string", "required": False, "description": desc, "match_mode": mode}


def _matcher_entry(
    *,
    policy_field: str,
    finding_field: str,
    mode: str = "regex",
    optional: bool = True,
) -> Dict[str, Any]:
    return {
        "policy_field": policy_field,
        "finding_field": finding_field,
        "mode": mode,
        "optional_in_rule": optional,
    }


def matchers_from_spec(spec: ToolPolicySpec) -> Dict[str, Any]:
    """Map policy JSON field names to finding dict fields used at match time."""
    matchers: Dict[str, Any] = {}
    rule_field = spec.rule_id_field or "rule_id"
    matchers[spec.policy_rule_id_key] = _matcher_entry(
        policy_field=spec.policy_rule_id_key,
        finding_field=rule_field,
        mode=spec.rule_id_mode,
    )
    if spec.policy_path_key:
        path_field = spec.path_field or "path"
        matchers[spec.policy_path_key] = _matcher_entry(
            policy_field=spec.policy_path_key,
            finding_field=path_field,
            mode="regex",
        )
    if spec.policy_message_key and spec.message_field:
        matchers[spec.policy_message_key] = _matcher_entry(
            policy_field=spec.policy_message_key,
            finding_field=spec.message_field,
            mode="regex",
        )
    return matchers


def path_match_hint_from_spec(spec: ToolPolicySpec) -> str:
    parts: List[str] = []
    if spec.policy_path_key:
        parts.append(f"{spec.policy_path_key} matches finding `{spec.path_field or 'path'}`")
    if spec.policy_message_key and spec.message_field:
        parts.append(
            f"{spec.policy_message_key} matches finding `{spec.message_field}` (not advisory text unless that is the stored field)"
        )
    if spec.rule_id_mode == "regex":
        parts.append(f"{spec.policy_rule_id_key} is matched as regex against `{spec.rule_id_field or 'rule_id'}`")
    else:
        parts.append(f"{spec.policy_rule_id_key} is exact match on `{spec.rule_id_field or 'rule_id'}`")
    return "; ".join(parts)


def accepted_finding_fields_from_spec(spec: ToolPolicySpec) -> Dict[str, Any]:
    fields: Dict[str, Any] = {
        spec.policy_rule_id_key: _field_rule_id_spec(spec.rule_id_mode),
        "reason": _FIELD_REASON,
    }
    if spec.policy_path_key:
        fields[spec.policy_path_key] = {
            "type": "string",
            "required": False,
            "description": f"Regex against finding `{spec.path_field or 'path'}`. Omitted matches any.",
        }
    if spec.policy_message_key and spec.message_field:
        fields[spec.policy_message_key] = {
            "type": "string",
            "required": False,
            "description": f"Regex against finding `{spec.message_field}`. Omitted matches any.",
        }
    return fields


def _semgrep_extra_blocks() -> Dict[str, Any]:
    override_fields = accepted_finding_fields_from_spec(
        ToolPolicySpec(
            rule_id_field="rule_id",
            path_field="path",
            message_field="message",
            rule_id_mode="exact",
        )
    )
    override_fields["new_severity"] = _FIELD_NEW_SEVERITY
    return {
        "severity_overrides": {
            "type": "array",
            "items": {"type": "object", "fields": override_fields},
        },
        "dedupe": _DEDUPE_SEMGREP,
    }


def tool_block_from_meta(meta: PolicyToolMeta) -> Dict[str, Any]:
    block: Dict[str, Any] = {
        "policy_key": meta.policy_key,
        "display_names": list(meta.display_names),
        "matchers": matchers_from_spec(meta.policy_spec),
        "accepted_findings": {
            "type": "array",
            "items": {
                "type": "object",
                "fields": accepted_finding_fields_from_spec(meta.policy_spec),
            },
        },
    }
    if meta.extra_block_properties:
        block.update(_semgrep_extra_blocks() if meta.policy_key == "semgrep" else {})
    return block


def _meta_from_processor(proc: ReportProcessor) -> Optional[PolicyToolMeta]:
    if not proc.policy_key or not proc.policy_spec:
        return None
    names: List[str] = []
    if proc.ai_tool_name:
        names.append(proc.ai_tool_name)
    if proc.name and proc.name not in names:
        names.append(proc.name)
    extra = ("severity_overrides", "dedupe") if proc.policy_key == "semgrep" else None
    return PolicyToolMeta(
        policy_key=proc.policy_key,
        display_names=tuple(names) or (proc.policy_key,),
        policy_spec=proc.policy_spec,
        policy_example_snippet=proc.policy_example_snippet,
        extra_block_properties=extra,
    )


def discover_policy_tools() -> Dict[str, PolicyToolMeta]:
    """Load policy metadata from all plugin REPORT_PROCESSOR instances."""
    tools: Dict[str, PolicyToolMeta] = {}
    try:
        package = importlib.import_module("scanner.plugins")
    except ImportError:
        return tools

    for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
        if not is_pkg:
            continue
        try:
            processor_module = importlib.import_module(f"{module_name}.processor")
        except Exception:
            continue
        proc = getattr(processor_module, "REPORT_PROCESSOR", None)
        if not proc:
            continue
        meta = _meta_from_processor(proc)
        if meta:
            tools[meta.policy_key] = meta
    return tools


def resolve_policy_key(key: str, known: Optional[Set[str]] = None) -> Tuple[str, Optional[str]]:
    """Return (canonical_key, warning)."""
    k = (key or "").strip()
    if not k:
        return k, None
    known = known or set(discover_policy_tools().keys())
    if k in known:
        return k, None
    alias = POLICY_KEY_ALIASES.get(k)
    if alias and alias in known:
        return alias, f"Top-level key '{k}' is deprecated; use '{alias}'"
    return k, None


def display_name_to_policy_key() -> Dict[str, str]:
    """Map report/AI display tool names to policy_key."""
    out: Dict[str, str] = {}
    for meta in discover_policy_tools().values():
        for name in meta.display_names:
            out[name] = meta.policy_key
        out[meta.policy_key] = meta.policy_key
    return out


def policy_match_values_from_finding(
    finding: Dict[str, Any],
    spec: ToolPolicySpec,
) -> Dict[str, str]:
    """Values agents should use when writing policy regexes for this finding."""

    def _val(getter: Optional[Callable], field: Optional[str]) -> str:
        if getter is not None:
            v = getter(finding)
        elif field:
            v = finding.get(field, "")
        else:
            v = ""
        return str(v) if v is not None else ""

    out: Dict[str, str] = {}
    out[spec.policy_rule_id_key] = _val(spec.rule_id_getter, spec.rule_id_field)
    if spec.policy_path_key:
        out[spec.policy_path_key] = _val(spec.path_getter, spec.path_field)
    if spec.policy_message_key and spec.message_field:
        out[spec.policy_message_key] = _val(spec.message_getter, spec.message_field)
    return out


def build_tool_blocks(
    tools_filter: Optional[Set[str]] = None,
) -> Dict[str, Dict[str, Any]]:
    all_meta = discover_policy_tools()
    keys = sorted(all_meta.keys())
    if tools_filter:
        keys = sorted(k for k in keys if k in tools_filter)
    return {k: tool_block_from_meta(all_meta[k]) for k in keys}


def build_path_match_hints(tools_filter: Optional[Set[str]] = None) -> Dict[str, str]:
    all_meta = discover_policy_tools()
    hints: Dict[str, str] = {}
    for pk, meta in sorted(all_meta.items()):
        if tools_filter and pk not in tools_filter:
            continue
        hints[pk] = path_match_hint_from_spec(meta.policy_spec)
    return hints
