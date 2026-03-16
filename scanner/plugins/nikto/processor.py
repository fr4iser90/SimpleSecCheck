#!/usr/bin/env python3
from scanner.output.processor_registry import ReportProcessor
import sys
import html
import json
import re

def debug(msg):
    print(f"[nikto_processor] {msg}", file=sys.stderr)

def nikto_summary(nikto_json):
    findings = []
    if nikto_json and isinstance(nikto_json, dict):
        # Parse Nikto JSON output
        scan_details = nikto_json.get('scan_details', {})
        for host, details in scan_details.items():
            # Extract findings
            items = details.get('items', [])
            for item in items:
                finding = {
                    'osvdb': item.get('osvdb', ''),
                    'osvdb_link': item.get('osvdb_link', ''),
                    'name': item.get('name', ''),
                    'description': item.get('description', ''),
                    'full_name': item.get('full_name', ''),
                    'target_ip': details.get('target_ip', ''),
                    'host_ip': details.get('host_ip', ''),
                    'hostname': host
                }
                findings.append(finding)
    else:
        debug("No Nikto results found in JSON.")
    return findings

def generate_nikto_html_section(nikto_findings):
    html_parts = []
    html_parts.append('<h2>Nikto Web Server Scan</h2>')
    if nikto_findings:
        html_parts.append('<table><tr><th>Finding</th><th>Description</th><th>Host</th></tr>')
        for finding in nikto_findings:
            name_escaped = html.escape(str(finding.get('name', '')))
            description_escaped = html.escape(str(finding.get('description', '')))
            hostname_escaped = html.escape(str(finding.get('hostname', '')))
            html_parts.append(f'<tr><td>{name_escaped}</td><td>{description_escaped}</td><td>{hostname_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No vulnerabilities found.</div>')
    return "".join(html_parts)


def _matches_pattern(value, pattern):
    if pattern is None: return True
    if value is None: value = ""
    try: return re.search(pattern, str(value)) is not None
    except re.error: return False


def _matches_nikto_rule(finding, rule):
    rule_ok = rule.get("rule_id") is None or _matches_pattern(finding.get("name", ""), rule.get("rule_id"))
    path_ok = _matches_pattern(finding.get("hostname", "") or finding.get("target_ip", ""), rule.get("path_regex"))
    msg_ok = _matches_pattern(finding.get("description", ""), rule.get("message_regex"))
    return rule_ok and path_ok and msg_ok


def _accept_record_nikto(finding, reason):
    return {"tool": "Nikto", "reason": reason or "Accepted by policy", "id": finding.get("name", ""), "path": finding.get("hostname", "") or finding.get("target_ip", ""), "line": "", "message": finding.get("description", "")}


def apply_nikto_policy(findings, tool_policy):
    if not findings: return [], []
    accepted_rules = tool_policy.get("accepted_findings", [])
    accepted_records = []
    processed = []
    for finding in findings:
        accepted = next((r for r in accepted_rules if _matches_nikto_rule(finding, r)), None)
        if accepted:
            accepted_records.append(_accept_record_nikto(finding, accepted.get("reason", "Accepted by policy")))
            continue
        processed.append(finding)
    return processed, accepted_records


NIKTO_POLICY_EXAMPLE = '''  "nikto": {
    "accepted_findings": [
      {
        "rule_id": "Server.*disclosure",
        "path_regex": ".*",
        "message_regex": "X-Powered-By|Server:",
        "reason": "Server header stripped at reverse proxy"
      }
    ]
  }'''

REPORT_PROCESSOR = ReportProcessor(
    name="Nikto",
    summary_func=nikto_summary,
    html_func=generate_nikto_html_section,
    ai_normalizer=lambda findings: [
        {
            "tool": "Nikto",
            "severity": str(f.get("severity", f.get("Severity", "UNKNOWN"))).upper(),
            "rule_id": str(f.get("rule_id", f.get("id", f.get("name", "")))),
            "path": str(f.get("path", f.get("file", f.get("filename", f.get("hostname", "")))),
            "line": str(f.get("line", f.get("line_number", f.get("start", "")))),
            "message": str(f.get("message", f.get("description", f.get("title", "")))),
        }
        for f in (findings or [])
    ],
    json_file="report.json",
    policy_key="nikto",
    apply_policy=apply_nikto_policy,
    policy_example_snippet=NIKTO_POLICY_EXAMPLE,
)