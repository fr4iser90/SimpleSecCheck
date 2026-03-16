#!/usr/bin/env python3
from scanner.output.processor_registry import ReportProcessor
import sys
import html
import re
from collections import defaultdict

def debug(msg):
    print(f"[semgrep_processor] {msg}", file=sys.stderr)

def semgrep_summary(semgrep_json):
    findings = []
    if semgrep_json and 'results' in semgrep_json:
        for r in semgrep_json['results']:
            finding = {
                'rule_id': r.get('check_id', ''),  # Semgrep JSON uses 'check_id', we normalize to 'rule_id'
                'path': r.get('path', ''),
                'start': r.get('start', {}).get('line', ''),
                'message': r.get('extra', {}).get('message', ''),
                'severity': r.get('extra', {}).get('severity', '')
            }
            findings.append(finding)
    else:
        debug("No Semgrep results found in JSON.")
    return findings

def generate_semgrep_html_section(semgrep_findings):
    html_parts = []
    html_parts.append('<h2>Semgrep Static Code Analysis</h2>')
    if semgrep_findings:
        html_parts.append('<table><tr><th>Rule</th><th>File</th><th>Line</th><th>Message</th><th>Severity</th></tr>')
        for finding in semgrep_findings:
            sev = finding['severity'].upper()
            icon = ''
            if sev == 'CRITICAL':
                icon = '🚨'
            elif sev == 'HIGH':
                icon = '🚨'
            elif sev == 'MEDIUM':
                icon = '⚠️'
            elif sev == 'LOW':
                icon = 'ℹ️'
            elif sev in ('INFO', 'INFORMATIONAL'):
                icon = 'ℹ️'

            rule_id_escaped = html.escape(str(finding.get("rule_id", "")))
            path_escaped = html.escape(str(finding.get("path", "")))
            start_escaped = html.escape(str(finding.get("start", "")))
            message = str(finding.get("message", ""))
            if finding.get("consolidated_count", 1) > 1:
                span = finding.get("line_span", "")
                message = f'{message} [Consolidated {finding.get("consolidated_count")} similar findings'
                if span:
                    message += f' around lines {span}'
                message += ']'
            message_escaped = html.escape(message)
            sev_escaped = html.escape(str(sev))

            html_parts.append(
                f'<tr class="row-{sev_escaped}"><td>{rule_id_escaped}</td><td>{path_escaped}</td>'
                f'<td>{start_escaped}</td><td>{message_escaped}</td>'
                f'<td class="severity-{sev_escaped}">{icon} {sev_escaped}</td></tr>'
            )
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No code vulnerabilities found.</div>')
    return "".join(html_parts)


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
    rule_ok = rule.get("rule_id") is None or rule.get("rule_id") == finding.get("rule_id")
    path_ok = _matches_pattern(finding.get("path", ""), rule.get("path_regex"))
    msg_ok = _matches_pattern(finding.get("message", ""), rule.get("message_regex"))
    return rule_ok and path_ok and msg_ok


def _accept_record_semgrep(finding, reason):
    return {
        "tool": "Semgrep",
        "reason": reason or "Accepted by policy",
        "id": finding.get("rule_id", ""),
        "path": finding.get("path", ""),
        "line": finding.get("start", ""),
        "message": finding.get("message", ""),
    }


def _dedupe_semgrep(findings, line_window=2):
    if not findings:
        return findings
    grouped = defaultdict(list)
    for finding in findings:
        key = (
            str(finding.get("rule_id", "")),
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


def apply_semgrep_policy(findings, tool_policy):
    if not findings:
        return [], []
    severity_overrides = tool_policy.get("severity_overrides", [])
    accepted_rules = tool_policy.get("accepted_findings", [])
    accepted_records = []
    processed = []
    for finding in findings:
        updated = dict(finding)
        for override in severity_overrides:
            if _matches_semgrep_rule(updated, override):
                new_sev = str(override.get("new_severity", "")).strip().upper()
                if new_sev:
                    updated["severity"] = new_sev
        accepted = None
        for rule in accepted_rules:
            if _matches_semgrep_rule(updated, rule):
                accepted = rule
                break
        if accepted:
            accepted_records.append(_accept_record_semgrep(updated, accepted.get("reason", "Accepted by policy")))
            continue
        processed.append(updated)
    dedupe_cfg = tool_policy.get("dedupe", {})
    if dedupe_cfg.get("enabled", True):
        line_window = int(dedupe_cfg.get("line_window", 2))
        processed = _dedupe_semgrep(processed, line_window=line_window)
    return processed, accepted_records


SEMGREP_POLICY_EXAMPLE = '''  "semgrep": {
    "severity_overrides": [
      {
        "rule_id": "python.django.security.debug-true.debug-true",
        "path_regex": "settings_dev\\\\.py$",
        "new_severity": "INFO",
        "reason": "DEBUG=True is intentional for development settings"
      }
    ],
    "accepted_findings": [
      {
        "rule_id": "generic.secrets.security.hardcoded-secret.hardcoded-secret",
        "path_regex": "src/examples/.*",
        "message_regex": "just_an_example",
        "reason": "Example key in demonstration file, not a real secret"
      }
    ],
    "dedupe": {
      "enabled": true,
      "line_window": 2
    }
  }'''

REPORT_PROCESSOR = ReportProcessor(
    name="Semgrep",
    summary_func=semgrep_summary,
    html_func=generate_semgrep_html_section,
    ai_normalizer=lambda findings: [
        {
            "tool": "Semgrep",
            "severity": str(f.get("severity", f.get("Severity", "UNKNOWN"))).upper(),
            "rule_id": str(f.get("rule_id", f.get("id", ""))),
            "path": str(f.get("path", f.get("file", f.get("filename", "")))),
            "line": str(f.get("line", f.get("line_number", f.get("start", "")))),
            "message": str(f.get("message", f.get("description", f.get("title", "")))),
        }
        for f in (findings or [])
    ],
    json_file="report.json",
    policy_key="semgrep",
    apply_policy=apply_semgrep_policy,
    policy_example_snippet=SEMGREP_POLICY_EXAMPLE,
)