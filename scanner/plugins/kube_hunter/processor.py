#!/usr/bin/env python3
from scanner.output.processor_registry import ReportProcessor
import sys
import html
import json

import re

def debug(msg):
    print(f"[kube_hunter_processor] {msg}", file=sys.stderr)

def kube_hunter_summary(kube_hunter_json):
    findings = []
    if kube_hunter_json and isinstance(kube_hunter_json, dict):
        # Parse Kube-hunter JSON output
        vulnerability_records = kube_hunter_json.get('vulnerabilities', [])
        for vuln in vulnerability_records:
            finding = {
                'vid': vuln.get('vid', ''),
                'category': vuln.get('category', ''),
                'description': vuln.get('description', ''),
                'evidence': vuln.get('evidence', ''),
                'hunter': vuln.get('hunter', ''),
                'location': vuln.get('location', ''),
                'severity': vuln.get('severity', ''),
                'vulnerability': vuln.get('vulnerability', ''),
                'discovered_nodes': vuln.get('discovered_nodes', {})
            }
            findings.append(finding)
    elif kube_hunter_json and isinstance(kube_hunter_json, str):
        # Try to parse JSON string
        try:
            data = json.loads(kube_hunter_json)
            if isinstance(data, dict):
                vulnerability_records = data.get('vulnerabilities', [])
                for vuln in vulnerability_records:
                    finding = {
                        'vid': vuln.get('vid', ''),
                        'category': vuln.get('category', ''),
                        'description': vuln.get('description', ''),
                        'evidence': vuln.get('evidence', ''),
                        'hunter': vuln.get('hunter', ''),
                        'location': vuln.get('location', ''),
                        'severity': vuln.get('severity', ''),
                        'vulnerability': vuln.get('vulnerability', ''),
                        'discovered_nodes': vuln.get('discovered_nodes', {})
                    }
                    findings.append(finding)
        except json.JSONDecodeError:
            debug("Failed to parse Kube-hunter JSON as string.")
    else:
        debug("No Kube-hunter results found in JSON.")
    return findings

def generate_kube_hunter_html_section(kube_hunter_findings):
    html_parts = []
    html_parts.append('<h2>Kube-hunter Kubernetes Security Scan</h2>')
    if kube_hunter_findings:
        html_parts.append('<table><tr><th>Vulnerability</th><th>Severity</th><th>Category</th><th>Location</th><th>Description</th></tr>')
        for finding in kube_hunter_findings:
            vuln_escaped = html.escape(str(finding.get('vulnerability', '')))
            severity_escaped = html.escape(str(finding.get('severity', '')))
            category_escaped = html.escape(str(finding.get('category', '')))
            location_escaped = html.escape(str(finding.get('location', '')))
            description_escaped = html.escape(str(finding.get('description', '')))
            
            # Color-code severity
            severity_class = "sev-MEDIUM"
            icon = '⚠️'
            if finding.get('severity', '').upper() == 'HIGH':
                severity_class = "sev-HIGH"
                icon = '🚨'
            elif finding.get('severity', '').upper() in ['LOW', 'INFO', 'INFORMATIONAL']:
                severity_class = "sev-LOW"
                icon = 'ℹ️'
            
            html_parts.append(f'<tr class="row-{finding.get("severity", "MEDIUM").upper()}"><td>{vuln_escaped}</td><td class="severity-{finding.get("severity", "MEDIUM").upper()}">{icon} {severity_escaped}</td><td>{category_escaped}</td><td>{location_escaped}</td><td>{description_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No Kubernetes vulnerabilities found.</div>')
    return "".join(html_parts)


def _matches_pattern(value, pattern):
    if pattern is None: return True
    if value is None: value = ""
    try: return re.search(pattern, str(value)) is not None
    except re.error: return False


def _matches_kube_hunter_rule(finding, rule):
    rule_ok = rule.get("rule_id") is None or _matches_pattern(finding.get("vulnerability", "") or finding.get("vid", ""), rule.get("rule_id"))
    path_ok = _matches_pattern(finding.get("location", "") or finding.get("category", ""), rule.get("path_regex"))
    msg_ok = _matches_pattern(finding.get("description", ""), rule.get("message_regex"))
    return rule_ok and path_ok and msg_ok


def _accept_record_kube_hunter(finding, reason):
    return {"tool": "Kube-hunter", "reason": reason or "Accepted by policy", "id": finding.get("vulnerability", "") or finding.get("vid", ""), "path": finding.get("location", ""), "line": "", "message": finding.get("description", "")}


def apply_kube_hunter_policy(findings, tool_policy):
    if not findings: return [], []
    accepted_rules = tool_policy.get("accepted_findings", [])
    accepted_records = []
    processed = []
    for finding in findings:
        accepted = next((r for r in accepted_rules if _matches_kube_hunter_rule(finding, r)), None)
        if accepted:
            accepted_records.append(_accept_record_kube_hunter(finding, accepted.get("reason", "Accepted by policy")))
            continue
        processed.append(finding)
    return processed, accepted_records


KUBE_HUNTER_POLICY_EXAMPLE = '''  "kube_hunter": {
    "accepted_findings": [
      {
        "rule_id": "Kube Dashboard Exposed",
        "path_regex": ".*",
        "message_regex": "informational|info",
        "reason": "Dashboard behind VPN, not public"
      }
    ]
  }'''

REPORT_PROCESSOR = ReportProcessor(
    name="Kube-hunter",
    summary_func=kube_hunter_summary,
    html_func=generate_kube_hunter_html_section,
    ai_normalizer=lambda findings: [
        {
            "tool": "Kube-hunter",
            "severity": str(f.get("severity", f.get("Severity", "UNKNOWN"))).upper(),
            "rule_id": str(f.get("rule_id", f.get("id", f.get("vulnerability", f.get("vid", ""))))),
            "path": str(f.get("path", f.get("file", f.get("filename", f.get("location", "")))),
            "line": str(f.get("line", f.get("line_number", f.get("start", "")))),
            "message": str(f.get("message", f.get("description", f.get("title", "")))),
        }
        for f in (findings or [])
    ],
    json_file="report.json",
    policy_key="kube_hunter",
    apply_policy=apply_kube_hunter_policy,
    policy_example_snippet=KUBE_HUNTER_POLICY_EXAMPLE,
)