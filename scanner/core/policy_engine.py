#!/usr/bin/env python3
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from scanner.core.policy_matching import (
    matches_path_for_policy,
    normalize_finding_paths,
    normalize_policy_path,
)


def safe_regex_search(pattern: Optional[str], value: Any) -> bool:
    if pattern is None:
        return True
    if value is None:
        value = ""
    try:
        return re.search(pattern, str(value)) is not None
    except re.error:
        return False


@dataclass(frozen=True)
class ToolPolicySpec:
    rule_id_field: Optional[str] = "rule_id"
    path_field: Optional[str] = "path"
    message_field: Optional[str] = "message"

    rule_id_getter: Optional[Callable[[Dict[str, Any]], Any]] = None
    path_getter: Optional[Callable[[Dict[str, Any]], Any]] = None
    message_getter: Optional[Callable[[Dict[str, Any]], Any]] = None

    rule_id_mode: str = "exact"
    accepted_rules_key: str = "accepted_findings"

    policy_rule_id_key: str = "rule_id"
    policy_path_key: str = "path_regex"
    policy_message_key: Optional[str] = "message_regex"

    accept_tool: str = ""
    accept_id_key: str = "id"
    accept_path_key: str = "path"
    accept_line_key: str = "line"
    accept_message_key: str = "message"

    accept_id_getter: Optional[Callable[[Dict[str, Any]], Any]] = None
    accept_path_getter: Optional[Callable[[Dict[str, Any]], Any]] = None
    accept_line_getter: Optional[Callable[[Dict[str, Any]], Any]] = None
    accept_message_getter: Optional[Callable[[Dict[str, Any]], Any]] = None


def rule_matches_spec(
    *,
    finding: Dict[str, Any],
    rule: Dict[str, Any],
    spec: ToolPolicySpec,
) -> bool:
    rule_id_pat = rule.get(spec.policy_rule_id_key)
    if spec.rule_id_getter is not None:
        finding_rule_id = spec.rule_id_getter(finding)
    else:
        finding_rule_id = finding.get(spec.rule_id_field or "rule_id")
    if rule_id_pat is None:
        rule_ok = True
    elif spec.rule_id_mode == "regex":
        rule_ok = safe_regex_search(str(rule_id_pat), finding_rule_id)
    else:
        rule_ok = str(rule_id_pat) == str(finding_rule_id)

    if spec.path_getter is not None:
        finding_path = spec.path_getter(finding)
    else:
        finding_path = finding.get(spec.path_field or "path", "")
    path_ok = matches_path_for_policy(finding_path, rule.get(spec.policy_path_key))

    if spec.policy_message_key is None or spec.message_field is None:
        msg_ok = True
    else:
        if spec.message_getter is not None:
            finding_message = spec.message_getter(finding)
        else:
            finding_message = finding.get(spec.message_field, "")
        msg_ok = safe_regex_search(rule.get(spec.policy_message_key), finding_message)

    return bool(rule_ok and path_ok and msg_ok)


def apply_policy_generic(
    *,
    findings: Iterable[Dict[str, Any]],
    tool_policy: Dict[str, Any],
    spec: ToolPolicySpec,
    accept_record: Callable[[Dict[str, Any], Optional[str]], Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    findings_list = list(findings or [])
    if not findings_list:
        return [], []

    accepted_rules = tool_policy.get(spec.accepted_rules_key, []) or []
    accepted_records: List[Dict[str, Any]] = []
    processed: List[Dict[str, Any]] = []

    for finding in findings_list:
        accepted = None
        for rule in accepted_rules:
            if rule_matches_spec(finding=finding, rule=rule, spec=spec):
                accepted = rule
                break
        if accepted:
            accepted_records.append(accept_record(finding, accepted.get("reason", "Accepted by policy")))
            continue
        processed.append(normalize_finding_paths(finding))

    return processed, accepted_records


def dedupe_findings_by_line_window(
    findings: List[Dict[str, Any]],
    *,
    group_fields: Tuple[str, ...],
    line_field: str = "start",
    line_window: int = 2,
) -> List[Dict[str, Any]]:
    if not findings:
        return findings
    grouped: Dict[Tuple[str, ...], List[Dict[str, Any]]] = defaultdict(list)
    for finding in findings:
        key = tuple(str(finding.get(f, "")) for f in group_fields)
        grouped[key].append(finding)

    deduped: List[Dict[str, Any]] = []
    for items in grouped.values():
        normalized = []
        for item in items:
            item_copy = dict(item)
            try:
                line_no = int(item_copy.get(line_field, 0))
            except (TypeError, ValueError):
                line_no = 0
            item_copy["_line"] = line_no
            normalized.append(item_copy)
        normalized.sort(key=lambda x: x["_line"])
        clusters: List[List[Dict[str, Any]]] = []
        for item in normalized:
            if not clusters:
                clusters.append([item])
                continue
            if abs(item["_line"] - clusters[-1][-1]["_line"]) <= line_window:
                clusters[-1].append(item)
            else:
                clusters.append([item])
        for cluster in clusters:
            anchor = dict(cluster[0])
            lines = [c["_line"] for c in cluster if c["_line"] > 0]
            if len(cluster) > 1:
                anchor["consolidated_count"] = len(cluster)
                if lines:
                    anchor["line_span"] = f"{min(lines)}-{max(lines)}"
            anchor.pop("_line", None)
            deduped.append(anchor)
    return deduped


def _cap_findings_per_rule(
    findings: List[Dict[str, Any]],
    *,
    rule_field: str,
    max_per_rule: int,
) -> List[Dict[str, Any]]:
    if max_per_rule <= 0:
        return findings
    counts: Dict[str, int] = defaultdict(int)
    capped: List[Dict[str, Any]] = []
    for finding in findings:
        rule_key = str(finding.get(rule_field, ""))
        if counts[rule_key] >= max_per_rule:
            continue
        counts[rule_key] += 1
        capped.append(finding)
    return capped


def _apply_dedupe_config(
    findings: List[Dict[str, Any]],
    *,
    dedupe_cfg: Dict[str, Any],
    spec: ToolPolicySpec,
) -> List[Dict[str, Any]]:
    if not dedupe_cfg or not dedupe_cfg.get("enabled", True):
        return findings

    rule_field = spec.rule_id_field or "rule_id"
    path_field = spec.path_field or "path"
    message_field = spec.message_field or "message"

    group_fields = dedupe_cfg.get("group_fields")
    if not group_fields:
        group_fields = [rule_field, path_field, "message", "severity"]
    line_field = str(
        dedupe_cfg.get(
            "line_field",
            "start" if spec.accept_line_getter is not None else "line",
        )
    )
    line_window = dedupe_cfg.get("line_window")
    if line_window is None:
        line_window = 2
    line_window = int(line_window)

    processed = dedupe_findings_by_line_window(
        findings,
        group_fields=tuple(group_fields),
        line_field=line_field,
        line_window=line_window,
    )

    max_per_rule = dedupe_cfg.get("max_deduped_per_rule")
    if max_per_rule is not None:
        try:
            processed = _cap_findings_per_rule(
                processed,
                rule_field=rule_field,
                max_per_rule=int(max_per_rule),
            )
        except (TypeError, ValueError):
            pass
    return processed


def apply_policy_with_severity_overrides(
    *,
    findings: Iterable[Dict[str, Any]],
    tool_policy: Dict[str, Any],
    spec: ToolPolicySpec,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    findings_list = list(findings or [])
    if not findings_list:
        return [], []

    severity_overrides = tool_policy.get("severity_overrides", [])
    processed: List[Dict[str, Any]] = []
    for finding in findings_list:
        updated = dict(finding)
        for override in severity_overrides:
            if rule_matches_spec(finding=updated, rule=override, spec=spec):
                new_sev = str(override.get("new_severity", "")).strip().upper()
                if new_sev:
                    updated["severity"] = new_sev
        processed.append(normalize_finding_paths(updated))

    processed, accepted_records = apply_policy_generic(
        findings=processed,
        tool_policy={"accepted_findings": tool_policy.get("accepted_findings", [])},
        spec=spec,
        accept_record=accept_record_from_spec(spec),
    )

    processed = [normalize_finding_paths(f) for f in processed]
    processed = _apply_dedupe_config(
        processed,
        dedupe_cfg=tool_policy.get("dedupe", {}) or {},
        spec=spec,
    )
    return processed, accepted_records


def accept_record_from_spec(spec: ToolPolicySpec) -> Callable[[Dict[str, Any], Optional[str]], Dict[str, Any]]:
    def _accept_record(finding: Dict[str, Any], reason: Optional[str]) -> Dict[str, Any]:
        if spec.accept_id_getter is not None:
            rec_id = spec.accept_id_getter(finding)
        else:
            rec_id = finding.get(spec.rule_id_field or "rule_id", "")

        if spec.accept_path_getter is not None:
            rec_path = spec.accept_path_getter(finding)
        else:
            rec_path = finding.get(spec.path_field or "path", "")

        if spec.accept_line_getter is not None:
            rec_line = spec.accept_line_getter(finding)
        else:
            rec_line = finding.get("line", finding.get("line_number", finding.get("start", "")))

        if spec.accept_message_getter is not None:
            rec_msg = spec.accept_message_getter(finding)
        else:
            rec_msg = "" if spec.message_field is None else finding.get(spec.message_field, "")

        return {
            "tool": spec.accept_tool or "",
            "reason": reason or "Accepted by policy",
            spec.accept_id_key: rec_id or "",
            spec.accept_path_key: normalize_policy_path(str(rec_path or "")),
            spec.accept_line_key: str(rec_line) if rec_line is not None else "",
            spec.accept_message_key: rec_msg or "",
        }

    return _accept_record
