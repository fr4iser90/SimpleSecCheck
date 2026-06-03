"""
Finding policy JSON schema — API and AI prompts.

Built from scanner plugin processors (policy_key + ToolPolicySpec) via policy_schema_registry.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Set

from domain.policies.finding_policy import DEFAULT_FINDING_POLICY_PATH

FINDING_POLICY_SCHEMA_VERSION = "2"

try:
    from scanner.core.policy_schema_registry import (
        POLICY_KEY_ALIASES,
        build_path_match_hints,
        build_tool_blocks,
        discover_policy_tools,
    )
except ImportError:
    POLICY_KEY_ALIASES = {}
    build_path_match_hints = None  # type: ignore
    build_tool_blocks = None  # type: ignore
    discover_policy_tools = None  # type: ignore

NOTES: List[str] = [
    "File must be valid JSON (not YAML).",
    "Root is a JSON object; each top-level value must be a JSON object (tool block).",
    f"Default path in repository: {DEFAULT_FINDING_POLICY_PATH}",
    "Top-level keys must match policy_key values in tools map (not UI display names).",
    "Use GET /api/v1/finding-policy/schema?tools=npm_audit,owasp_dc to fetch only relevant tools.",
    "Each tool block includes matchers: policy JSON field -> finding field used at scan time.",
    "Findings in API/AI output include policy_key and policy_match for correct regex values.",
    "Deprecated aliases (e.g. owasp_dependency_check) are accepted at load time and mapped to owasp_dc.",
    "Validate before commit: POST /api/v1/finding-policy/validate",
    "Omitted rule fields match any value for that field.",
    "Semgrep dedupe is configured under semgrep.dedupe, not at root.",
    "Inline suppressions are separate; see inline_suppression_syntax in schema response.",
]

INLINE_SUPPRESSION_SYNTAX: Dict[str, List[str]] = {
    "python": ["# nosec", "# nosec B608", "# nosemgrep: rule-id", "# ssc:accept rule-id — reason"],
    "javascript": ["// eslint-disable-next-line rule-id", "// nosemgrep: rule-id"],
    "gitleaks": ["# gitleaks:allow"],
}

INLINE_SUPPRESSION_ENV: Dict[str, str] = {
    "SSC_INLINE_SUPPRESSIONS_ENABLED": "Default true. Set false/0/off to disable reading inline tags at report time.",
    "SSC_INLINE_SUPPRESSIONS_LINE_LOOKBACK": "Default 1. Lines above finding to check for multi-line statements.",
    "SSC_INLINE_SUPPRESSIONS_CROSS_TOOL_NOSEC": "Default true. Apply # nosec Bxxx to non-Bandit tools when id matches.",
    "SSC_INLINE_SUPPRESSIONS_CROSS_TOOL_NOSEMGREP": "Default true. Apply # nosemgrep to non-Semgrep tools when rule matches.",
}

MINIMAL_EXAMPLE: Dict[str, Any] = {
    "semgrep": {
        "accepted_findings": [
            {
                "rule_id": "EXAMPLE_RULE_ID",
                "path_regex": "EXAMPLE_PATH_REGEX",
                "message_regex": "EXAMPLE_MESSAGE_REGEX",
                "reason": "EXAMPLE_REASON",
            }
        ],
    },
}


def _fallback_tool_blocks() -> Dict[str, Any]:
    """Minimal schema when scanner package is not importable (e.g. isolated backend tests)."""
    standard = {
        "accepted_findings": {
            "type": "array",
            "items": {
                "type": "object",
                "fields": {
                    "rule_id": {"type": "string", "required": False},
                    "path_regex": {"type": "string", "required": False},
                    "message_regex": {"type": "string", "required": False},
                    "reason": {"type": "string", "required": True},
                },
            },
        }
    }
    return {k: dict(standard) for k in ("semgrep", "bandit", "npm_audit", "owasp_dc")}


def get_finding_policy_schema(
    *,
    tools_filter: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """Build full schema dict, optionally filtered to specific policy_key names."""
    if build_tool_blocks is None:
        tools_out = _fallback_tool_blocks()
        path_hints: Dict[str, str] = {}
    else:
        if tools_filter:
            known = set(discover_policy_tools().keys())
            unknown = tools_filter - known
            if unknown:
                tools_filter = tools_filter & known
        tools_out = build_tool_blocks(tools_filter=tools_filter)
        path_hints = build_path_match_hints(tools_filter=tools_filter)

    return {
        "schema_version": FINDING_POLICY_SCHEMA_VERSION,
        "default_path": DEFAULT_FINDING_POLICY_PATH,
        "format": "json",
        "rules": {
            "root_type": "object",
            "block_value_type": "object",
            "validation": "Root dict; every top-level value must be a dict. Keys must be policy_key values.",
        },
        "policy_key_aliases": dict(POLICY_KEY_ALIASES),
        "notes": NOTES,
        "inline_suppression_syntax": INLINE_SUPPRESSION_SYNTAX,
        "inline_suppression_env": INLINE_SUPPRESSION_ENV,
        "path_match_hints": path_hints,
        "tools": tools_out,
        "minimal_example": MINIMAL_EXAMPLE,
    }


def policy_keys_from_findings(findings: List[Dict[str, Any]]) -> Set[str]:
    """Resolve policy_key set from normalized finding dicts (API / AI prompt)."""
    keys: Set[str] = set()
    try:
        from scanner.core.policy_schema_registry import display_name_to_policy_key
    except ImportError:
        display_name_to_policy_key = lambda: {}  # type: ignore

    name_map = display_name_to_policy_key()
    for f in findings:
        if not isinstance(f, dict):
            continue
        pk = (f.get("policy_key") or "").strip()
        if pk:
            keys.add(pk)
            continue
        tool = (f.get("tool") or "").strip()
        if tool and tool in name_map:
            keys.add(name_map[tool])
    return keys


def format_policy_schema_markdown(
    *,
    policy_path: str = DEFAULT_FINDING_POLICY_PATH,
    language: str = "english",
    tools_filter: Optional[Set[str]] = None,
) -> str:
    """Markdown section for AI prompts (english / german / chinese)."""
    schema = get_finding_policy_schema(tools_filter=tools_filter)
    tools = schema["tools"]
    lang = (language or "english").lower()

    tool_lines = []
    for policy_key, block in sorted(tools.items()):
        display = ", ".join(block.get("display_names") or [policy_key])
        matchers = block.get("matchers") or {}
        matcher_lines = []
        for pname, m in sorted(matchers.items()):
            if isinstance(m, dict):
                matcher_lines.append(
                    f"`{pname}` → finding `{m.get('finding_field', '?')}` ({m.get('mode', 'regex')})"
                )
        props = []
        for prop_name, prop_def in block.items():
            if prop_name in ("policy_key", "display_names", "matchers"):
                continue
            if prop_def.get("type") == "array":
                item_fields = prop_def.get("items", {}).get("fields", {})
                field_names = ", ".join(f"`{k}`" for k in item_fields)
                props.append(f"`{prop_name}[]`: {{ {field_names} }}")
            elif prop_def.get("type") == "object":
                inner = prop_def.get("fields", {})
                inner_names = ", ".join(f"`{k}`" for k in inner)
                props.append(f"`{prop_name}`: {{ {inner_names} }}")
        line = f"- `{policy_key}` (display: {display}): " + "; ".join(props)
        if matcher_lines:
            line += "\n  - Matchers: " + "; ".join(matcher_lines)
        tool_lines.append(line)

    example = schema["minimal_example"]
    example_str = json.dumps(example, indent=2, ensure_ascii=False)
    aliases = schema.get("policy_key_aliases") or {}
    alias_lines = [
        f"  - `{alias}` → `{target}`" for alias, target in sorted(aliases.items())
    ]
    alias_section = ""
    if alias_lines:
        alias_section = "\n### Deprecated key aliases (auto-mapped at load)\n" + "\n".join(alias_lines) + "\n"

    if lang == "german":
        header = (
            "\n\n## Finding-Policy JSON-Schema (MUSS exakt eingehalten werden)\n"
            "Output muss **valide JSON** sein. Top-Level-Keys = **policy_key** (z. B. `owasp_dc`), nicht UI-Namen.\n"
            "Nutzen Sie `policy_match` aus den Findings für Regex-Werte.\n\n"
            "### Root-Form\n"
            f"- Datei: `{policy_path}`\n"
            "- Root: `{ <policy_key>: <object>, ... }`\n\n"
            "### Tool-Blöcke\n"
        )
        footer = alias_section + (
            "\n\n### Minimales Beispiel\n"
            f"```json\n{example_str}\n```\n"
        )
    elif lang == "chinese":
        header = (
            "\n\n## Finding policy JSON 结构（必须严格遵守）\n"
            "输出必须是合法 JSON。顶层 key 为 **policy_key**（如 `owasp_dc`），不是 UI 显示名。\n"
            "使用 findings 中的 `policy_match` 填写正则。\n\n"
            "### 根结构\n"
            f"- 文件: `{policy_path}`\n"
            "- 根: `{ <policy_key>: <object>, ... }`\n\n"
            "### 工具块\n"
        )
        footer = alias_section + (
            "\n\n### 最小示例\n"
            f"```json\n{example_str}\n```\n"
        )
    else:
        header = (
            "\n\n## Finding policy JSON schema (MUST follow exactly)\n"
            "Output must be **valid JSON**. Top-level keys are **policy_key** values (e.g. `owasp_dc`), not UI labels.\n"
            "Use `policy_match` from each finding when writing regex patterns.\n\n"
            "### Root shape\n"
            f"- File: `{policy_path}`\n"
            "- Root: `{ <policy_key>: <object>, ... }`\n\n"
            "### Tool blocks\n"
        )
        footer = alias_section + (
            "\n\n### Minimal example skeleton\n"
            f"```json\n{example_str}\n```\n"
        )

    return header + "\n".join(tool_lines) + footer


def parse_tools_query(tools_param: Optional[str]) -> Optional[Set[str]]:
    """Parse comma-separated policy_key list; None = all tools."""
    if not tools_param or not str(tools_param).strip():
        return None
    keys = {t.strip() for t in str(tools_param).split(",") if t.strip()}
    return keys or None
