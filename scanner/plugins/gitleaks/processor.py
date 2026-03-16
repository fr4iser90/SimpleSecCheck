#!/usr/bin/env python3
from scanner.output.processor_registry import ReportProcessor
import sys
import html
import json
import re

def debug(msg):
    print(f"[gitleaks_processor] {msg}", file=sys.stderr)

def gitleaks_summary(gitleaks_json):
    findings = []
    if gitleaks_json and isinstance(gitleaks_json, list):
        for r in gitleaks_json:
            finding = {
                'rule_id': r.get('RuleID', ''),
                'description': r.get('Description', ''),
                'file': r.get('File', ''),
                'line': r.get('StartLine', 0),
                'secret': r.get('Secret', ''),
                'commit': r.get('Commit', ''),
                'author': r.get('Author', ''),
                'date': r.get('Date', '')
            }
            findings.append(finding)
    elif gitleaks_json and isinstance(gitleaks_json, str):
        # Try to parse JSON string
        try:
            data = json.loads(gitleaks_json)
            if isinstance(data, list):
                for r in data:
                    finding = {
                        'rule_id': r.get('RuleID', ''),
                        'description': r.get('Description', ''),
                        'file': r.get('File', ''),
                        'line': r.get('StartLine', 0),
                        'secret': r.get('Secret', ''),
                        'commit': r.get('Commit', ''),
                        'author': r.get('Author', ''),
                        'date': r.get('Date', '')
                    }
                    findings.append(finding)
        except json.JSONDecodeError:
            debug("Failed to parse GitLeaks JSON as string.")
    else:
        debug("No GitLeaks results found in JSON.")
    return findings

def generate_gitleaks_html_section(gitleaks_findings):
    html_parts = []
    html_parts.append('<h2>GitLeaks Secret Detection</h2>')
    if gitleaks_findings:
        html_parts.append('<table><tr><th>Rule ID</th><th>File</th><th>Line</th><th>Description</th></tr>')
        for finding in gitleaks_findings:
            rule_id_escaped = html.escape(str(finding.get("rule_id", "")))
            file_escaped = html.escape(str(finding.get("file", "")))
            line_escaped = html.escape(str(finding.get("line", "")))
            description_escaped = html.escape(str(finding.get("description", "")))
            
            html_parts.append(f'<tr><td>{rule_id_escaped}</td><td>{file_escaped}</td><td>{line_escaped}</td><td>{description_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No secrets detected.</div>')
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


def _matches_gitleaks_rule(finding, rule):
    rule_ok = rule.get("rule_id") is None or rule.get("rule_id") == finding.get("rule_id")
    path_ok = _matches_pattern(finding.get("file", ""), rule.get("file_regex"))
    desc_ok = _matches_pattern(finding.get("description", ""), rule.get("description_regex"))
    return rule_ok and path_ok and desc_ok


def _accept_record_gitleaks(finding, reason):
    return {
        "tool": "GitLeaks",
        "reason": reason or "Accepted by policy",
        "id": finding.get("rule_id", ""),
        "path": finding.get("file", ""),
        "line": finding.get("line", ""),
        "message": finding.get("description", ""),
    }


def apply_gitleaks_policy(findings, tool_policy):
    if not findings:
        return [], []
    accepted_rules = tool_policy.get("accepted_findings", [])
    accepted_records = []
    processed = []
    for finding in findings:
        accepted = None
        for rule in accepted_rules:
            if _matches_gitleaks_rule(finding, rule):
                accepted = rule
                break
        if accepted:
            accepted_records.append(_accept_record_gitleaks(finding, accepted.get("reason", "Accepted by policy")))
            continue
        processed.append(finding)
    return processed, accepted_records


GITLEAKS_POLICY_EXAMPLE = '''  "gitleaks": {
    "accepted_findings": [
      {
        "rule_id": "generic-api-key",
        "file_regex": "tests/.*",
        "description_regex": "test.*key",
        "reason": "Test files contain example keys, not real secrets"
      }
    ]
  }'''

REPORT_PROCESSOR = ReportProcessor(
    name="GitLeaks",
    summary_func=gitleaks_summary,
    html_func=generate_gitleaks_html_section,
    ai_normalizer=lambda findings: [
        {
            "tool": "GitLeaks",
            "severity": str(f.get("severity", f.get("Severity", "UNKNOWN"))).upper(),
            "rule_id": str(f.get("rule_id", f.get("id", ""))),
            "path": str(f.get("path", f.get("file", f.get("filename", "")))),
            "line": str(f.get("line", f.get("line_number", f.get("start", "")))),
            "message": str(f.get("message", f.get("description", f.get("title", "")))),
        }
        for f in (findings or [])
    ],
    json_file="report.json",
    policy_key="gitleaks",
    apply_policy=apply_gitleaks_policy,
    policy_example_snippet=GITLEAKS_POLICY_EXAMPLE,
)