#!/usr/bin/env python3
from scanner.output.processor_registry import ReportProcessor
import sys
import html
import re

def debug(msg):
    print(f"[wapiti_processor] {msg}", file=sys.stderr)

def wapiti_summary(wapiti_json):
    findings = []
    if wapiti_json and isinstance(wapiti_json, dict):
        # Wapiti JSON structure: vulnerabilities is a dict of {vuln_type: {url: [info]}}
        vulnerabilities = wapiti_json.get('vulnerabilities', {})
        if isinstance(vulnerabilities, dict):
            for vuln_type, vuln_data in vulnerabilities.items():
                if isinstance(vuln_data, dict):
                    for url, vuln_details in vuln_data.items():
                        if isinstance(vuln_details, list):
                            for vuln in vuln_details:
                                if isinstance(vuln, dict):
                                    finding = {
                                        'category': vuln_type,
                                        'description': vuln.get('desc', vuln.get('description', '')),
                                        'reference': str(vuln.get('ref', {})),
                                        'target': url,
                                        'info': vuln
                                    }
                                    findings.append(finding)
    else:
        debug("No Wapiti results found in JSON.")
    return findings

def generate_wapiti_html_section(wapiti_findings):
    html_parts = []
    html_parts.append('<h2>Wapiti Web Vulnerability Scan</h2>')
    if wapiti_findings:
        html_parts.append('<table><tr><th>Category</th><th>Description</th><th>Target</th></tr>')
        for finding in wapiti_findings:
            category_escaped = html.escape(str(finding.get('category', '')))
            description_escaped = html.escape(str(finding.get('description', '')))
            target_escaped = html.escape(str(finding.get('target', '')))
            html_parts.append(f'<tr><td>{category_escaped}</td><td>{description_escaped}</td><td>{target_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No vulnerabilities found.</div>')
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


def _matches_wapiti_rule(finding, rule):
    rule_ok = rule.get("rule_id") is None or _matches_pattern(finding.get("category", ""), rule.get("rule_id"))
    path_ok = _matches_pattern(finding.get("target", ""), rule.get("path_regex"))
    msg_ok = _matches_pattern(finding.get("description", ""), rule.get("message_regex"))
    return rule_ok and path_ok and msg_ok


def _accept_record_wapiti(finding, reason):
    return {
        "tool": "Wapiti",
        "reason": reason or "Accepted by policy",
        "id": finding.get("category", ""),
        "path": finding.get("target", ""),
        "line": "",
        "message": finding.get("description", ""),
    }


def apply_wapiti_policy(findings, tool_policy):
    if not findings:
        return [], []
    accepted_rules = tool_policy.get("accepted_findings", [])
    accepted_records = []
    processed = []
    for finding in findings:
        accepted = None
        for rule in accepted_rules:
            if _matches_wapiti_rule(finding, rule):
                accepted = rule
                break
        if accepted:
            accepted_records.append(_accept_record_wapiti(finding, accepted.get("reason", "Accepted by policy")))
            continue
        processed.append(finding)
    return processed, accepted_records


WAPITI_POLICY_EXAMPLE = '''  "wapiti": {
    "accepted_findings": [
      {
        "rule_id": "cookie",
        "path_regex": "https?://.*",
        "message_regex": "Missing.*HttpOnly",
        "reason": "Legacy cookie on internal app, migration planned"
      }
    ]
  }'''

REPORT_PROCESSOR = ReportProcessor(
    name="Wapiti",
    summary_func=wapiti_summary,
    html_func=generate_wapiti_html_section,
    ai_normalizer=lambda findings: [
        {
            "tool": "Wapiti",
            "severity": str(f.get("severity", f.get("Severity", "UNKNOWN"))).upper(),
            "rule_id": str(f.get("rule_id", f.get("id", f.get("category", "")))),
            "path": str(f.get("path", f.get("file", f.get("filename", f.get("target", "")))),
            "line": str(f.get("line", f.get("line_number", f.get("start", "")))),
            "message": str(f.get("message", f.get("description", f.get("title", "")))),
        }
        for f in (findings or [])
    ],
    json_file="report.json",
    policy_key="wapiti",
    apply_policy=apply_wapiti_policy,
    policy_example_snippet=WAPITI_POLICY_EXAMPLE,
)