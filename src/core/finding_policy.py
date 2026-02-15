#!/usr/bin/env python3
import json
import os
import re
import sys
from collections import defaultdict


def debug(msg):
    print(f"[finding_policy] {msg}", file=sys.stderr)


def load_policy(policy_path):
    if not policy_path:
        return {}
    if not os.path.exists(policy_path):
        debug(f"Policy file not found: {policy_path}")
        return {}
    try:
        with open(policy_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception as exc:
        debug(f"Failed to load policy file {policy_path}: {exc}")
        return {}


def _matches_pattern(value, pattern):
    if pattern is None:
        return True
    if value is None:
        value = ""
    try:
        return re.search(pattern, str(value)) is not None
    except re.error:
        return False


def _matches_semgrep_rule(finding, rule):
    check_ok = rule.get("check_id") is None or rule.get("check_id") == finding.get("check_id")
    path_ok = _matches_pattern(finding.get("path", ""), rule.get("path_regex"))
    msg_ok = _matches_pattern(finding.get("message", ""), rule.get("message_regex"))
    return check_ok and path_ok and msg_ok


def _matches_gitleaks_rule(finding, rule):
    rule_ok = rule.get("rule_id") is None or rule.get("rule_id") == finding.get("rule_id")
    path_ok = _matches_pattern(finding.get("file", ""), rule.get("file_regex"))
    desc_ok = _matches_pattern(finding.get("description", ""), rule.get("description_regex"))
    return rule_ok and path_ok and desc_ok


def _accept_record(tool, finding, reason):
    record = {
        "tool": tool,
        "reason": reason or "Accepted by policy",
    }
    if tool == "Semgrep":
        record.update(
            {
                "id": finding.get("check_id", ""),
                "path": finding.get("path", ""),
                "line": finding.get("start", ""),
                "message": finding.get("message", ""),
            }
        )
    elif tool == "GitLeaks":
        record.update(
            {
                "id": finding.get("rule_id", ""),
                "path": finding.get("file", ""),
                "line": finding.get("line", ""),
                "message": finding.get("description", ""),
            }
        )
    return record


def apply_semgrep_policy(findings, semgrep_policy):
    if not findings:
        return [], []

    severity_overrides = semgrep_policy.get("severity_overrides", [])
    accepted_rules = semgrep_policy.get("accepted_findings", [])

    accepted_records = []
    processed = []

    for finding in findings:
        updated = dict(finding)

        for override in severity_overrides:
            if _matches_semgrep_rule(updated, override):
                new_severity = str(override.get("new_severity", "")).strip().upper()
                if new_severity:
                    updated["severity"] = new_severity

        accepted = None
        for rule in accepted_rules:
            if _matches_semgrep_rule(updated, rule):
                accepted = rule
                break
        if accepted:
            accepted_records.append(
                _accept_record("Semgrep", updated, accepted.get("reason", "Accepted Semgrep finding"))
            )
            continue

        processed.append(updated)

    dedupe_cfg = semgrep_policy.get("dedupe", {})
    if dedupe_cfg.get("enabled", True):
        line_window = int(dedupe_cfg.get("line_window", 2))
        processed = dedupe_semgrep(processed, line_window=line_window)

    return processed, accepted_records


def dedupe_semgrep(findings, line_window=2):
    if not findings:
        return findings

    grouped = defaultdict(list)
    for finding in findings:
        key = (
            str(finding.get("check_id", "")),
            str(finding.get("path", "")),
            str(finding.get("message", "")),
            str(finding.get("severity", "")),
        )
        grouped[key].append(finding)

    deduped = []
    for _, items in grouped.items():
        normalized = []
        for item in items:
            item_copy = dict(item)
            try:
                line_no = int(item_copy.get("start", 0))
            except Exception:
                line_no = 0
            item_copy["_line"] = line_no
            normalized.append(item_copy)

        normalized.sort(key=lambda x: x["_line"])

        clusters = []
        for item in normalized:
            if not clusters:
                clusters.append([item])
                continue
            prev_cluster = clusters[-1]
            if abs(item["_line"] - prev_cluster[-1]["_line"]) <= line_window:
                prev_cluster.append(item)
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


def apply_gitleaks_policy(findings, gitleaks_policy):
    if not findings:
        return [], []

    accepted_rules = gitleaks_policy.get("accepted_findings", [])
    accepted_records = []
    processed = []

    for finding in findings:
        accepted = None
        for rule in accepted_rules:
            if _matches_gitleaks_rule(finding, rule):
                accepted = rule
                break
        if accepted:
            accepted_records.append(
                _accept_record("GitLeaks", finding, accepted.get("reason", "Accepted GitLeaks finding"))
            )
            continue
        processed.append(finding)

    return processed, accepted_records
