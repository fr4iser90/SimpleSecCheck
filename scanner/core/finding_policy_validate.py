#!/usr/bin/env python3
"""Validate finding-policy.json against discovered scanner policy metadata."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from scanner.core.policy_engine import ToolPolicySpec, rule_matches_spec
from scanner.core.policy_schema_registry import (
    POLICY_KEY_ALIASES,
    build_tool_blocks,
    discover_policy_tools,
    resolve_policy_key,
)


def _allowed_rule_keys(block: Dict[str, Any], policy_key: str) -> Set[str]:
    tools = build_tool_blocks(tools_filter={policy_key})
    tool_def = tools.get(policy_key) or {}
    fields: Set[str] = set()
    for prop_name, prop_def in tool_def.items():
        if prop_name in ("policy_key", "display_names", "matchers"):
            continue
        if prop_def.get("type") == "array":
            item_fields = prop_def.get("items", {}).get("fields", {})
            fields.update(item_fields.keys())
    return fields


def _block_property_keys(policy_key: str) -> Set[str]:
    tools = build_tool_blocks(tools_filter={policy_key})
    tool_def = tools.get(policy_key) or {}
    return {
        k
        for k in tool_def
        if k not in ("policy_key", "display_names", "matchers")
    }


def _validate_regex_field(name: str, value: Any, errors: List[str], warnings: List[str]) -> None:
    if value is None:
        return
    if not isinstance(value, str):
        errors.append(f"{name}: must be a string")
        return
    try:
        re.compile(value)
    except re.error as exc:
        errors.append(f"{name}: invalid regex: {exc}")


def validate_policy_data(
    data: Dict[str, Any],
    *,
    sample_findings: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    """
    Validate policy root object.

    sample_findings: optional map policy_key -> list of raw finding dicts for dry-run match counts.
    """
    errors: List[str] = []
    warnings: List[str] = []
    dry_run: Dict[str, Any] = {}

    if not isinstance(data, dict):
        return {"valid": False, "errors": ["Policy root must be a JSON object"], "warnings": warnings}

    known = set(discover_policy_tools().keys())
    meta_by_key = discover_policy_tools()
    tool_policies: Dict[str, Dict[str, Any]] = {}

    for key, value in data.items():
        if not isinstance(value, dict):
            warnings.append(f"Ignoring non-object top-level key '{key}' (same as scanner load_policy)")
            continue
        canonical, hint = resolve_policy_key(key, known)
        if hint:
            warnings.append(hint)
        if canonical not in known:
            suggestions = [
                alias_target
                for alias, alias_target in POLICY_KEY_ALIASES.items()
                if alias_target in known and key.lower() in alias.lower()
            ]
            msg = f"Unknown policy tool key '{key}'"
            if canonical != key:
                msg += f" (resolved to '{canonical}')"
            if suggestions:
                msg += f"; did you mean: {', '.join(sorted(set(suggestions)))}?"
            elif known:
                msg += f"; known keys include: {', '.join(sorted(known)[:8])}..."
            errors.append(msg)
            continue
        if canonical in tool_policies and key != canonical:
            warnings.append(f"Duplicate tool block for '{canonical}' (keys '{key}' and earlier entry)")
        tool_policies[canonical] = value

    for policy_key, block in tool_policies.items():
        allowed_props = _block_property_keys(policy_key)
        for prop in block:
            if prop not in allowed_props:
                errors.append(f"{policy_key}: unknown property '{prop}'")

        meta = meta_by_key[policy_key]
        spec = meta.policy_spec

        for rules_key in ("accepted_findings", "severity_overrides"):
            rules = block.get(rules_key)
            if rules is None:
                continue
            if not isinstance(rules, list):
                errors.append(f"{policy_key}.{rules_key}: must be an array")
                continue
            allowed_fields = _allowed_rule_keys(block, policy_key)
            if rules_key == "severity_overrides":
                allowed_fields = set(allowed_fields)

            samples = (sample_findings or {}).get(policy_key) or []
            findings_would_accept = 0

            for idx, rule in enumerate(rules):
                if not isinstance(rule, dict):
                    errors.append(f"{policy_key}.{rules_key}[{idx}]: must be an object")
                    continue
                for field in rule:
                    if field not in allowed_fields:
                        errors.append(
                            f"{policy_key}.{rules_key}[{idx}]: unknown field '{field}'"
                        )
                if "reason" not in rule and rules_key == "accepted_findings":
                    errors.append(f"{policy_key}.{rules_key}[{idx}]: missing required 'reason'")
                if rules_key == "severity_overrides" and "new_severity" not in rule:
                    errors.append(f"{policy_key}.{rules_key}[{idx}]: missing required 'new_severity'")

                for regex_key in (
                    spec.policy_path_key,
                    spec.policy_message_key,
                    "path_regex",
                    "message_regex",
                    "file_regex",
                    "description_regex",
                ):
                    if regex_key and regex_key in rule:
                        _validate_regex_field(
                            f"{policy_key}.{rules_key}[{idx}].{regex_key}",
                            rule[regex_key],
                            errors,
                            warnings,
                        )
                if spec.rule_id_mode == "regex" and spec.policy_rule_id_key in rule:
                    _validate_regex_field(
                        f"{policy_key}.{rules_key}[{idx}].{spec.policy_rule_id_key}",
                        rule[spec.policy_rule_id_key],
                        errors,
                        warnings,
                    )

            if samples and rules_key == "accepted_findings":
                for finding in samples:
                    if not isinstance(finding, dict):
                        continue
                    for rule in rules:
                        if isinstance(rule, dict) and rule_matches_spec(
                            finding=finding, rule=rule, spec=spec
                        ):
                            findings_would_accept += 1
                            break

            if samples and rules_key == "accepted_findings":
                dry_run[policy_key] = {
                    "findings_checked": len(samples),
                    "rules": len(rules),
                    "findings_would_accept": findings_would_accept,
                    "would_accept_any": findings_would_accept > 0,
                }

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "dry_run": dry_run,
        "known_policy_keys": sorted(known),
        "aliases": dict(POLICY_KEY_ALIASES),
    }
