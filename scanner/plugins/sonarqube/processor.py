#!/usr/bin/env python3
from scanner.output.processor_registry import ReportProcessor
"""
SonarQube Processor for SimpleSecCheck
Processes SonarQube results and generates HTML report sections
"""

import json
import os
import sys
import html
import re

def debug(msg):
    print(f"[sonarqube_processor] {msg}", file=sys.stderr)

def sonarqube_summary(sonarqube_json):
    findings = []
    if sonarqube_json and isinstance(sonarqube_json, dict):
        # Handle SonarQube JSON format
        issues = sonarqube_json.get('issues', [])
        
        for issue in issues:
            finding = {
                'severity': issue.get('severity', 'INFO'),
                'component': issue.get('component', ''),
                'message': issue.get('message', ''),
                'line': issue.get('line', 0),
                'rule': issue.get('rule', ''),
                'type': issue.get('type', 'CODE_SMELL')
            }
            
            findings.append(finding)
    else:
        debug("No SonarQube results found in JSON.")
    return findings

def generate_sonarqube_html_section(sonarqube_findings):
    html_parts = []
    html_parts.append('<h2>SonarQube Code Quality & Security Scan</h2>')
    if sonarqube_findings:
        html_parts.append('<table><tr><th>Severity</th><th>Component</th><th>Line</th><th>Message</th></tr>')
        for finding in sonarqube_findings:
            sev = finding['severity'].upper()
            icon = ''
            if sev == 'BLOCKER': icon = '🚨'
            elif sev == 'CRITICAL': icon = '🚨'
            elif sev == 'MAJOR': icon = '⚠️'
            elif sev == 'MINOR': icon = 'ℹ️'
            elif sev in ('INFO', 'INFORMATIONAL'): icon = 'ℹ️'
            
            severity_escaped = html.escape(str(sev))
            component_escaped = html.escape(str(finding.get("component", "")))
            line_escaped = html.escape(str(finding.get("line", "")))
            message_escaped = html.escape(str(finding.get("message", "")))

            html_parts.append(f'<tr class="row-{severity_escaped}"><td class="severity-{severity_escaped}">{icon} {severity_escaped}</td><td>{component_escaped}</td><td>{line_escaped}</td><td>{message_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No code quality issues found.</div>')
    return "".join(html_parts)


def _matches_pattern(value, pattern):
    if pattern is None: return True
    if value is None: value = ""
    try: return re.search(pattern, str(value)) is not None
    except re.error: return False


def _matches_sonarqube_rule(finding, rule):
    rule_ok = rule.get("rule_id") is None or _matches_pattern(finding.get("rule", ""), rule.get("rule_id"))
    path_ok = _matches_pattern(finding.get("component", ""), rule.get("path_regex"))
    msg_ok = _matches_pattern(finding.get("message", ""), rule.get("message_regex"))
    return rule_ok and path_ok and msg_ok


def _accept_record_sonarqube(finding, reason):
    return {"tool": "SonarQube", "reason": reason or "Accepted by policy", "id": finding.get("rule", ""), "path": finding.get("component", ""), "line": str(finding.get("line", "")), "message": finding.get("message", "")}


def apply_sonarqube_policy(findings, tool_policy):
    if not findings: return [], []
    accepted_rules = tool_policy.get("accepted_findings", [])
    accepted_records = []
    processed = []
    for finding in findings:
        accepted = next((r for r in accepted_rules if _matches_sonarqube_rule(finding, r)), None)
        if accepted:
            accepted_records.append(_accept_record_sonarqube(finding, accepted.get("reason", "Accepted by policy")))
            continue
        processed.append(finding)
    return processed, accepted_records


SONARQUBE_POLICY_EXAMPLE = '''  "sonarqube": {
    "accepted_findings": [
      {
        "rule_id": "javascript:S1848",
        "path_regex": ".*\\.test\\.[jt]s$",
        "message_regex": "console\\.",
        "reason": "Console in test files only"
      }
    ]
  }'''

REPORT_PROCESSOR = ReportProcessor(
    name="SonarQube",
    summary_func=sonarqube_summary,
    html_func=generate_sonarqube_html_section,
    ai_normalizer=lambda findings: [
        {
            "tool": "SonarQube",
            "severity": str(f.get("severity", f.get("Severity", "UNKNOWN"))).upper(),
            "rule_id": str(f.get("rule_id", f.get("id", f.get("rule", "")))),
            "path": str(f.get("path", f.get("file", f.get("filename", f.get("component", "")))),
            "line": str(f.get("line", f.get("line_number", f.get("start", "")))),
            "message": str(f.get("message", f.get("description", f.get("title", "")))),
        }
        for f in (findings or [])
    ],
    json_file="report.json",
    policy_key="sonarqube",
    apply_policy=apply_sonarqube_policy,
    policy_example_snippet=SONARQUBE_POLICY_EXAMPLE,
)