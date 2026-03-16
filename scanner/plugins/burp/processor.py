#!/usr/bin/env python3
from scanner.output.processor_registry import ReportProcessor
import sys
import html
import json
import re

def debug(msg):
    print(f"[burp_processor] {msg}", file=sys.stderr)

def burp_summary(burp_json):
    findings = []
    if burp_json and isinstance(burp_json, dict):
        # Parse Burp Suite JSON output
        vulnerabilities = burp_json.get('vulnerabilities', [])
        for vuln in vulnerabilities:
            finding = {
                'name': vuln.get('name', ''),
                'description': vuln.get('description', ''),
                'severity': vuln.get('severity', ''),
                'host': vuln.get('host', ''),
                'path': vuln.get('path', ''),
                'remediation': vuln.get('remediation', '')
            }
            findings.append(finding)
    else:
        debug("No Burp Suite results found in JSON.")
    return findings

def generate_burp_html_section(burp_findings):
    html_parts = []
    html_parts.append('<h2>Burp Suite Web Application Security Scan</h2>')
    if burp_findings:
        html_parts.append('<table><tr><th>Finding</th><th>Severity</th><th>Host</th><th>Path</th><th>Description</th></tr>')
        for finding in burp_findings:
            name_escaped = html.escape(str(finding.get('name', '')))
            severity_escaped = html.escape(str(finding.get('severity', '')))
            host_escaped = html.escape(str(finding.get('host', '')))
            path_escaped = html.escape(str(finding.get('path', '')))
            description_escaped = html.escape(str(finding.get('description', '')))
            
            # Add severity icons
            icon = ''
            sev_class = severity_escaped.upper()
            if sev_class in ('CRITICAL', 'HIGH'): 
                icon = '🚨'
            elif sev_class == 'MEDIUM': 
                icon = '⚠️'
            elif sev_class == 'LOW': 
                icon = 'ℹ️'
            
            html_parts.append(f'<tr class="row-{sev_class}"><td>{name_escaped}</td><td class="severity-{sev_class}">{icon} {severity_escaped}</td><td>{host_escaped}</td><td>{path_escaped}</td><td>{description_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No web application vulnerabilities found.</div>')
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


def _matches_burp_rule(finding, rule):
    rule_ok = rule.get("rule_id") is None or _matches_pattern(finding.get("name", ""), rule.get("rule_id"))
    path_ok = _matches_pattern(finding.get("path", "") or finding.get("host", ""), rule.get("path_regex"))
    msg_ok = _matches_pattern(finding.get("description", ""), rule.get("message_regex"))
    return rule_ok and path_ok and msg_ok


def _accept_record_burp(finding, reason):
    return {
        "tool": "Burp Suite",
        "reason": reason or "Accepted by policy",
        "id": finding.get("name", ""),
        "path": finding.get("path", "") or finding.get("host", ""),
        "line": "",
        "message": finding.get("description", ""),
    }


def apply_burp_policy(findings, tool_policy):
    if not findings:
        return [], []
    accepted_rules = tool_policy.get("accepted_findings", [])
    accepted_records = []
    processed = []
    for finding in findings:
        accepted = None
        for rule in accepted_rules:
            if _matches_burp_rule(finding, rule):
                accepted = rule
                break
        if accepted:
            accepted_records.append(_accept_record_burp(finding, accepted.get("reason", "Accepted by policy")))
            continue
        processed.append(finding)
    return processed, accepted_records


BURP_POLICY_EXAMPLE = '''  "burp_suite": {
    "accepted_findings": [
      {
        "rule_id": "Information disclosure",
        "path_regex": "/debug|/version",
        "message_regex": "version.*disclosure",
        "reason": "Version endpoint is internal-only, not exposed"
      }
    ]
  }'''

REPORT_PROCESSOR = ReportProcessor(
    name="Burp Suite",
    summary_func=burp_summary,
    html_func=generate_burp_html_section,
    ai_normalizer=lambda findings: [
        {
            "tool": "Burp Suite",
            "severity": str(f.get("severity", f.get("Severity", "UNKNOWN"))).upper(),
            "rule_id": str(f.get("rule_id", f.get("id", f.get("name", "")))),
            "path": str(f.get("path", f.get("file", f.get("filename", f.get("host", "")))),
            "line": str(f.get("line", f.get("line_number", f.get("start", "")))),
            "message": str(f.get("message", f.get("description", f.get("title", "")))),
        }
        for f in (findings or [])
    ],
    json_file="report.json",
    policy_key="burp_suite",
    apply_policy=apply_burp_policy,
    policy_example_snippet=BURP_POLICY_EXAMPLE,
)