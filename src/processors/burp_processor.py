#!/usr/bin/env python3
import sys
import html
import json

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

