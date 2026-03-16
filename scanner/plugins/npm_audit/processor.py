#!/usr/bin/env python3
from scanner.output.processor_registry import ReportProcessor
import sys
import html
import json
import re

def debug(msg):
    print(f"[npm_audit_processor] {msg}", file=sys.stderr)

def npm_audit_summary(npm_audit_json):
    findings = []
    if npm_audit_json and isinstance(npm_audit_json, dict):
        # Handle npm audit JSON format
        vulnerabilities = npm_audit_json.get('vulnerabilities', {})
        metadata = npm_audit_json.get('metadata', {})
        
        for package_name, vuln_data in vulnerabilities.items():
            finding = {
                'package': vuln_data.get('name', package_name),
                'severity': vuln_data.get('severity', 'MODERATE'),
                'is_direct': vuln_data.get('isDirect', False),
                'via': vuln_data.get('via', []),
                'effects': vuln_data.get('effects', []),
                'range': vuln_data.get('range', ''),
                'fix_available': vuln_data.get('fixAvailable', False),
                'dependency_path': ' > '.join(vuln_data.get('nodes', []))
            }
            findings.append(finding)
    else:
        debug("No npm audit results found in JSON.")
    return findings

def generate_npm_audit_html_section(npm_audit_findings):
    html_parts = []
    html_parts.append('<h2>npm audit Dependency Security Scan</h2>')
    if npm_audit_findings:
        html_parts.append('<table><tr><th>Package</th><th>Severity</th><th>Is Direct</th><th>Dependency Path</th><th>Fix Available</th></tr>')
        for finding in npm_audit_findings:
            sev = finding['severity'].upper()
            icon = ''
            if sev == 'CRITICAL': icon = '🚨'
            elif sev == 'HIGH': icon = '🚨'
            elif sev == 'MODERATE': icon = '⚠️'
            elif sev == 'LOW': icon = 'ℹ️'
            elif sev in ('INFO', 'INFORMATIONAL'): icon = 'ℹ️'
            
            is_direct = 'Yes' if finding.get('is_direct') else 'No'
            fix_available = 'Yes' if finding.get('fix_available') else 'No'
            
            package_escaped = html.escape(str(finding.get("package", "")))
            sev_escaped = html.escape(str(sev))
            is_direct_escaped = html.escape(str(is_direct))
            dep_path_escaped = html.escape(str(finding.get("dependency_path", "")))
            fix_available_escaped = html.escape(str(fix_available))

            html_parts.append(f'<tr class="row-{sev_escaped}"><td>{package_escaped}</td><td class="severity-{sev_escaped}">{icon} {sev_escaped}</td><td>{is_direct_escaped}</td><td>{dep_path_escaped}</td><td>{fix_available_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No npm dependency vulnerabilities found.</div>')
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


def _matches_npm_audit_rule(finding, rule):
    rule_ok = rule.get("rule_id") is None or _matches_pattern(finding.get("package", ""), rule.get("rule_id"))
    path_ok = _matches_pattern(finding.get("dependency_path", finding.get("package", "")), rule.get("path_regex"))
    msg_ok = _matches_pattern(finding.get("severity", ""), rule.get("message_regex"))
    return rule_ok and path_ok and msg_ok


def _accept_record_npm_audit(finding, reason):
    return {
        "tool": "npm audit",
        "reason": reason or "Accepted by policy",
        "id": finding.get("package", ""),
        "path": finding.get("dependency_path", finding.get("package", "")),
        "line": "",
        "message": finding.get("severity", ""),
    }


def apply_npm_audit_policy(findings, tool_policy):
    if not findings:
        return [], []
    accepted_rules = tool_policy.get("accepted_findings", [])
    accepted_records = []
    processed = []
    for finding in findings:
        accepted = None
        for rule in accepted_rules:
            if _matches_npm_audit_rule(finding, rule):
                accepted = rule
                break
        if accepted:
            accepted_records.append(_accept_record_npm_audit(finding, accepted.get("reason", "Accepted by policy")))
            continue
        processed.append(finding)
    return processed, accepted_records


NPM_AUDIT_POLICY_EXAMPLE = '''  "npm_audit": {
    "accepted_findings": [
      {
        "rule_id": "minimist",
        "path_regex": ".*",
        "message_regex": "low|moderate",
        "reason": "Low/minor dependency, accepted risk"
      }
    ]
  }'''

REPORT_PROCESSOR = ReportProcessor(
    name="npm audit",
    summary_func=npm_audit_summary,
    html_func=generate_npm_audit_html_section,
    ai_normalizer=lambda findings: [
        {
            "tool": "npm audit",
            "severity": str(f.get("severity", f.get("Severity", "UNKNOWN"))).upper(),
            "rule_id": str(f.get("rule_id", f.get("id", f.get("package", "")))),
            "path": str(f.get("path", f.get("file", f.get("filename", f.get("dependency_path", f.get("package", ""))))),
            "line": str(f.get("line", f.get("line_number", f.get("start", "")))),
            "message": str(f.get("message", f.get("description", f.get("title", f.get("severity", ""))))),
        }
        for f in (findings or [])
    ],
    json_file="report.json",
    policy_key="npm_audit",
    apply_policy=apply_npm_audit_policy,
    policy_example_snippet=NPM_AUDIT_POLICY_EXAMPLE,
)