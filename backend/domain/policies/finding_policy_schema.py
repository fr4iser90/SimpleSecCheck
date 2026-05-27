"""
Finding policy JSON schema — single source of truth for API and AI prompts.

Derived from scanner/plugins/*/processor.py (policy_key, apply_policy, matchers).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from domain.policies.finding_policy import DEFAULT_FINDING_POLICY_PATH

FINDING_POLICY_SCHEMA_VERSION = "1"

# --- Reusable field specs (match scanner processor behavior) ---

_FIELD_RULE_ID_EXACT = {
    "type": "string",
    "required": False,
    "description": "Rule/check ID; omitted matches any. Compared for exact equality (most tools).",
}

_FIELD_RULE_ID_REGEX = {
    "type": "string",
    "required": False,
    "description": "Rule/check ID as regex matched against finding rule_id (CodeQL only).",
}

_FIELD_PATH_REGEX = {
    "type": "string",
    "required": False,
    "description": "Regex against tool-specific path field (file, path, component, package, etc.). Omitted matches any.",
}

_FIELD_MESSAGE_REGEX = {
    "type": "string",
    "required": False,
    "description": "Regex against finding message/description. Omitted matches any.",
}

_FIELD_FILE_REGEX = {
    "type": "string",
    "required": False,
    "description": "Regex against GitLeaks file path. Omitted matches any.",
}

_FIELD_DESCRIPTION_REGEX = {
    "type": "string",
    "required": False,
    "description": "Regex against GitLeaks description. Omitted matches any.",
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

_ACCEPTED_STANDARD = {
    "type": "array",
    "items": {
        "type": "object",
        "fields": {
            "rule_id": _FIELD_RULE_ID_EXACT,
            "path_regex": _FIELD_PATH_REGEX,
            "message_regex": _FIELD_MESSAGE_REGEX,
            "reason": _FIELD_REASON,
        },
    },
}

_ACCEPTED_CODEQL = {
    "type": "array",
    "items": {
        "type": "object",
        "fields": {
            "rule_id": _FIELD_RULE_ID_REGEX,
            "path_regex": _FIELD_PATH_REGEX,
            "message_regex": _FIELD_MESSAGE_REGEX,
            "reason": _FIELD_REASON,
        },
    },
}

_ACCEPTED_GITLEAKS = {
    "type": "array",
    "items": {
        "type": "object",
        "fields": {
            "rule_id": _FIELD_RULE_ID_EXACT,
            "file_regex": _FIELD_FILE_REGEX,
            "description_regex": _FIELD_DESCRIPTION_REGEX,
            "reason": _FIELD_REASON,
        },
    },
}

_ACCEPTED_DETECT_SECRETS = {
    "type": "array",
    "items": {
        "type": "object",
        "fields": {
            "rule_id": {
                "type": "string",
                "required": False,
                "description": "Matched against detect-secrets type (not rule_id field). Omitted matches any.",
            },
            "path_regex": _FIELD_PATH_REGEX,
            "reason": _FIELD_REASON,
        },
    },
}

_SEVERITY_OVERRIDES_SEMGREP = {
    "type": "array",
    "items": {
        "type": "object",
        "fields": {
            "rule_id": _FIELD_RULE_ID_EXACT,
            "path_regex": _FIELD_PATH_REGEX,
            "message_regex": _FIELD_MESSAGE_REGEX,
            "new_severity": _FIELD_NEW_SEVERITY,
            "reason": _FIELD_REASON,
        },
    },
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
    },
}

# policy_key -> block schema (keys allowed inside each tool object)
TOOL_BLOCKS: Dict[str, Dict[str, Any]] = {}

_STANDARD_TOOLS = [
    "anchore",
    "android_manifest",
    "bandit",
    "brakeman",
    "burp_suite",
    "checkov",
    "clair",
    "docker_bench",
    "eslint",
    "ios_plist",
    "kube_bench",
    "kube_hunter",
    "nikto",
    "npm_audit",
    "nuclei",
    "owasp_dc",
    "safety",
    "snyk",
    "sonarqube",
    "terraform_checkov",
    "trivy",
    "trufflehog",
    "wapiti",
]

for _key in _STANDARD_TOOLS:
    TOOL_BLOCKS[_key] = {"accepted_findings": _ACCEPTED_STANDARD}

TOOL_BLOCKS["codeql"] = {"accepted_findings": _ACCEPTED_CODEQL}
TOOL_BLOCKS["gitleaks"] = {"accepted_findings": _ACCEPTED_GITLEAKS}
TOOL_BLOCKS["detect_secrets"] = {"accepted_findings": _ACCEPTED_DETECT_SECRETS}
TOOL_BLOCKS["semgrep"] = {
    "accepted_findings": _ACCEPTED_STANDARD,
    "severity_overrides": _SEVERITY_OVERRIDES_SEMGREP,
    "dedupe": _DEDUPE_SEMGREP,
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

NOTES: List[str] = [
    "File must be valid JSON (not YAML).",
    "Root is a JSON object; each top-level value must be a JSON object (tool block).",
    f"Default path in repository: {DEFAULT_FINDING_POLICY_PATH}",
    "Top-level keys must match scanner policy_key values (see tools map).",
    "Only include tool blocks for tools present in your scan findings.",
    "Omitted rule fields (rule_id, path_regex, etc.) match any value for that field.",
    "Semgrep dedupe is configured under the semgrep block (semgrep.dedupe), not at root.",
    "A root-level dedupe key is ignored by the scanner (legacy); use semgrep.dedupe instead.",
]

PATH_MATCH_HINTS: Dict[str, str] = {
    "bandit": "path_regex matches finding filename",
    "codeql": "path_regex matches finding path; rule_id is a regex",
    "gitleaks": "file_regex matches finding file; description_regex matches description",
    "detect_secrets": "rule_id matches secret type; path_regex matches filename",
    "semgrep": "path_regex matches finding path; message_regex matches message",
    "trivy": "path_regex matches PkgName",
    "npm_audit": "path_regex matches dependency_path or package",
    "snyk": "path_regex matches package name",
    "sonarqube": "path_regex matches component",
}


def get_finding_policy_schema(
    *,
    tools_filter: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """Build full schema dict, optionally filtered to specific policy_key names."""
    if tools_filter:
        unknown = tools_filter - set(TOOL_BLOCKS.keys())
        if unknown:
            tools_filter = tools_filter & set(TOOL_BLOCKS.keys())
        tools_out = {k: TOOL_BLOCKS[k] for k in sorted(tools_filter)}
    else:
        tools_out = dict(sorted(TOOL_BLOCKS.items()))

    return {
        "schema_version": FINDING_POLICY_SCHEMA_VERSION,
        "default_path": DEFAULT_FINDING_POLICY_PATH,
        "format": "json",
        "rules": {
            "root_type": "object",
            "block_value_type": "object",
            "validation": "Root dict; every top-level value must be a dict (see scanner/core/finding_policy.py).",
        },
        "notes": NOTES,
        "path_match_hints": {
            k: PATH_MATCH_HINTS[k]
            for k in sorted(tools_out.keys())
            if k in PATH_MATCH_HINTS
        },
        "tools": tools_out,
        "minimal_example": MINIMAL_EXAMPLE,
    }


def _format_fields_markdown(fields: Dict[str, Any]) -> str:
    parts = []
    for name, spec in fields.items():
        req = "required" if spec.get("required") else "optional"
        typ = spec.get("type", "string")
        extra = ""
        if "enum" in spec:
            extra = f", one of: {'|'.join(spec['enum'])}"
        parts.append(f"`{name}` ({typ}, {req}{extra})")
    return ", ".join(parts)


def _format_block_property_markdown(name: str, prop: Dict[str, Any]) -> str:
    if prop.get("type") == "array":
        item_fields = prop.get("items", {}).get("fields", {})
        return f"  - `{name}[]`: {{ {_format_fields_markdown(item_fields)} }}`"
    if prop.get("type") == "object":
        inner = prop.get("fields", {})
        return f"  - `{name}`: {{ {_format_fields_markdown(inner)} }}`"
    return f"  - `{name}`"


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
        props = []
        for prop_name, prop_def in block.items():
            if prop_def.get("type") == "array":
                item_fields = prop_def.get("items", {}).get("fields", {})
                field_names = ", ".join(f"`{k}`" for k in item_fields)
                props.append(f"`{prop_name}[]`: {{ {field_names} }}")
            elif prop_def.get("type") == "object":
                inner = prop_def.get("fields", {})
                inner_names = ", ".join(f"`{k}`" for k in inner)
                props.append(f"`{prop_name}`: {{ {inner_names} }}")
        tool_lines.append(f"- `{policy_key}`: " + "; ".join(props))

    example = schema["minimal_example"]
    import json

    example_str = json.dumps(example, indent=2, ensure_ascii=False)

    if lang == "german":
        header = (
            "\n\n## Finding-Policy JSON-Schema (MUSS exakt eingehalten werden)\n"
            "Output muss **valide JSON** sein (kein YAML). Root muss ein JSON-Objekt sein. "
            "Jeder Top-Level-Value muss ein JSON-Objekt sein.\n"
            "Nur diese Keys verwenden, wenn sie zum Tool passen. Keine neuen Felder erfinden.\n\n"
            "### Root-Form\n"
            f"- Datei: `{policy_path}`\n"
            "- Root: `{ <tool_policy_key>: <object>, ... }`\n\n"
            "### Tool-Blöcke und Felder\n"
        )
        footer = (
            "\n\n### Minimales Beispiel\n"
            f"```json\n{example_str}\n```\n"
        )
    elif lang == "chinese":
        header = (
            "\n\n## Finding policy JSON 结构（必须严格遵守）\n"
            "输出必须是**合法 JSON**（不是 YAML）。根必须是 JSON 对象。每个顶层 value 必须是 JSON 对象。\n"
            "只使用与工具匹配的字段，不要编造新字段。\n\n"
            "### 根结构\n"
            f"- 文件: `{policy_path}`\n"
            "- 根: `{ <tool_policy_key>: <object>, ... }`\n\n"
            "### 工具块与字段\n"
        )
        footer = (
            "\n\n### 最小示例\n"
            f"```json\n{example_str}\n```\n"
        )
    else:
        header = (
            "\n\n## Finding policy JSON schema (MUST follow exactly)\n"
            "Output must be **valid JSON** (not YAML). Root must be a JSON object. "
            "Each top-level value must be a JSON object.\n"
            "Only use these keys when relevant to the tool(s) in the findings. Do not invent new fields.\n\n"
            "### Root shape\n"
            f"- File: `{policy_path}`\n"
            "- Root: `{ <tool_policy_key>: <object>, ... }`\n\n"
            "### Supported tool blocks and fields\n"
        )
        footer = (
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
