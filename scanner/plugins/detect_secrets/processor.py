#!/usr/bin/env python3
from scanner.output.processor_registry import ReportProcessor
import sys
import html
import json

import re

def debug(msg):
    print(f"[detect_secrets_processor] {msg}", file=sys.stderr)

def detect_secrets_summary(detect_secrets_json):
    findings = []
    if detect_secrets_json and isinstance(detect_secrets_json, dict):
        results = detect_secrets_json.get('results', [])
        for filename, file_results in results.items():
            if isinstance(file_results, list):
                for r in file_results:
                    finding = {
                        'filename': filename,
                        'line_number': r.get('line_number', 0),
                        'type': r.get('type', ''),
                        'hashed_secret': r.get('hashed_secret', ''),
                        'is_secret': r.get('is_secret', False),
                        'is_verified': r.get('is_verified', False)
                    }
                    findings.append(finding)
    elif isinstance(detect_secrets_json, str):
        # Try to parse JSON string
        try:
            data = json.loads(detect_secrets_json)
            if isinstance(data, dict):
                results = data.get('results', [])
                for filename, file_results in results.items():
                    if isinstance(file_results, list):
                        for r in file_results:
                            finding = {
                                'filename': filename,
                                'line_number': r.get('line_number', 0),
                                'type': r.get('type', ''),
                                'hashed_secret': r.get('hashed_secret', ''),
                                'is_secret': r.get('is_secret', False),
                                'is_verified': r.get('is_verified', False)
                            }
                            findings.append(finding)
        except json.JSONDecodeError:
            debug("Failed to parse detect-secrets JSON as string.")
    else:
        debug("No detect-secrets results found in JSON.")
    return findings

def generate_detect_secrets_html_section(detect_secrets_findings):
    html_parts = []
    html_parts.append('<h2>Detect-secrets Secret Detection</h2>')
    if detect_secrets_findings:
        html_parts.append('<table><tr><th>Type</th><th>File</th><th>Line</th><th>Verified</th></tr>')
        for finding in detect_secrets_findings:
            verified = 'Yes' if finding.get('is_verified', False) else 'No'
            icon = '🚨' if finding.get('is_verified', False) else '⚠️'
            type_escaped = html.escape(str(finding.get("type", "")))
            filename_escaped = html.escape(str(finding.get("filename", "")))
            line_escaped = html.escape(str(finding.get("line_number", "")))
            verified_escaped = html.escape(str(verified))
            
            html_parts.append(f'<tr><td>{type_escaped}</td><td>{filename_escaped}</td><td>{line_escaped}</td><td>{verified_escaped} {icon}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No secrets detected.</div>')
    return "".join(html_parts)


def _matches_pattern(value, pattern):
    if pattern is None: return True
    if value is None: value = ""
    try: return re.search(pattern, str(value)) is not None
    except re.error: return False


def _matches_detect_secrets_rule(finding, rule):
    rule_ok = rule.get("rule_id") is None or _matches_pattern(finding.get("type", ""), rule.get("rule_id"))
    path_ok = _matches_pattern(finding.get("filename", ""), rule.get("path_regex"))
    return rule_ok and path_ok


def _accept_record_detect_secrets(finding, reason):
    return {"tool": "Detect-secrets", "reason": reason or "Accepted by policy", "id": finding.get("type", ""), "path": finding.get("filename", ""), "line": str(finding.get("line_number", "")), "message": ""}


def apply_detect_secrets_policy(findings, tool_policy):
    if not findings: return [], []
    accepted_rules = tool_policy.get("accepted_findings", [])
    accepted_records = []
    processed = []
    for finding in findings:
        accepted = next((r for r in accepted_rules if _matches_detect_secrets_rule(finding, r)), None)
        if accepted:
            accepted_records.append(_accept_record_detect_secrets(finding, accepted.get("reason", "Accepted by policy")))
            continue
        processed.append(finding)
    return processed, accepted_records


DETECT_SECRETS_POLICY_EXAMPLE = '''  "detect_secrets": {
    "accepted_findings": [
      {
        "rule_id": "Private Key",
        "path_regex": "tests/fixtures/.*\\.pem$",
        "reason": "Test fixture keys, not used in production"
      }
    ]
  }'''

REPORT_PROCESSOR = ReportProcessor(
    name="Detect-secrets",
    summary_func=detect_secrets_summary,
    html_func=generate_detect_secrets_html_section,
    ai_normalizer=lambda findings: [
        {
            "tool": "Detect-secrets",
            "severity": str(f.get("severity", f.get("Severity", "UNKNOWN"))).upper(),
            "rule_id": str(f.get("rule_id", f.get("id", f.get("type", "")))),
            "path": str(f.get("path", f.get("file", f.get("filename", "")))),
            "line": str(f.get("line", f.get("line_number", f.get("start", "")))),
            "message": str(f.get("message", f.get("description", f.get("title", "")))),
        }
        for f in (findings or [])
    ],
    json_file="report.json",
    policy_key="detect_secrets",
    apply_policy=apply_detect_secrets_policy,
    policy_example_snippet=DETECT_SECRETS_POLICY_EXAMPLE,
)