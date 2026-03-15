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

REPORT_PROCESSOR = ReportProcessor(
    name="SonarQube",
    summary_func=sonarqube_summary,
    html_func=generate_sonarqube_html_section,
    ai_normalizer=lambda findings: [
        {
            "tool": "SonarQube",
            "severity": str(f.get("severity", f.get("Severity", "UNKNOWN"))).upper(),
            "rule_id": str(f.get("rule_id", f.get("id", ""))),
            "path": str(f.get("path", f.get("file", f.get("filename", "")))),
            "line": str(f.get("line", f.get("line_number", f.get("start", "")))),
            "message": str(f.get("message", f.get("description", f.get("title", "")))),
        }
        for f in (findings or [])
    ],
    json_file="report.json",  # Changed from sonarqube.json
)