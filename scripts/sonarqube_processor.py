#!/usr/bin/env python3
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

