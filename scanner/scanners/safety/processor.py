#!/usr/bin/env python3
from scanner.reporting.processor_registry import ReportProcessor
import sys
import html
import json

def debug(msg):
    print(f"[safety_processor] {msg}", file=sys.stderr)

def safety_summary(safety_json):
    findings = []
    if safety_json and isinstance(safety_json, dict):
        # Handle Safety JSON format
        vulnerabilities = safety_json.get('vulnerabilities', [])
        packages = safety_json.get('packages', [])
        
        for vuln in vulnerabilities:
            finding = {
                'package': vuln.get('package', ''),
                'version': vuln.get('installed_version', ''),
                'vulnerability_id': vuln.get('vulnerability_id', ''),
                'severity': vuln.get('severity', 'MEDIUM'),
                'description': vuln.get('description', ''),
                'cve': vuln.get('cve', ''),
                'advisory': vuln.get('advisory', ''),
                'specs': vuln.get('specs', ''),
                'more_info_url': vuln.get('more_info_url', '')
            }
            findings.append(finding)
    else:
        debug("No Safety results found in JSON.")
    return findings

def generate_safety_html_section(safety_findings):
    html_parts = []
    html_parts.append('<h2>Safety Python Dependency Security Scan</h2>')
    if safety_findings:
        html_parts.append('<table><tr><th>Package</th><th>Version</th><th>Vulnerability ID</th><th>Severity</th><th>Description</th></tr>')
        for finding in safety_findings:
            sev = finding['severity'].upper()
            icon = ''
            if sev == 'CRITICAL': icon = '🚨'
            elif sev == 'HIGH': icon = '🚨'
            elif sev == 'MEDIUM': icon = '⚠️'
            elif sev == 'LOW': icon = 'ℹ️'
            elif sev in ('INFO', 'INFORMATIONAL'): icon = 'ℹ️'
            
            package_escaped = html.escape(str(finding.get("package", "")))
            version_escaped = html.escape(str(finding.get("version", "")))
            vuln_id_escaped = html.escape(str(finding.get("vulnerability_id", "")))
            sev_escaped = html.escape(str(sev))
            desc_escaped = html.escape(str(finding.get("description", "")))

            html_parts.append(f'<tr class="row-{sev_escaped}"><td>{package_escaped}</td><td>{version_escaped}</td><td>{vuln_id_escaped}</td><td class="severity-{sev_escaped}">{icon} {sev_escaped}</td><td>{desc_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No Python dependency vulnerabilities found.</div>')
    return "".join(html_parts)

REPORT_PROCESSOR = ReportProcessor(
    name="Safety",
    summary_func=safety_summary,
    html_func=generate_safety_html_section,
    ai_normalizer=lambda findings: [
        {
            "tool": "Safety",
            "severity": str(f.get("severity", f.get("Severity", "UNKNOWN"))).upper(),
            "rule_id": str(f.get("rule_id", f.get("id", ""))),
            "path": str(f.get("path", f.get("file", f.get("filename", "")))),
            "line": str(f.get("line", f.get("line_number", f.get("start", "")))),
            "message": str(f.get("message", f.get("description", f.get("title", "")))),
        }
        for f in (findings or [])
    ],
    json_file="safety.json",
)