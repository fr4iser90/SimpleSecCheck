#!/usr/bin/env python3
import sys
import html
import json

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

