#!/usr/bin/env python3
from scanner.output.processor_registry import ReportProcessor
import sys
import html
import json

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

REPORT_PROCESSOR = ReportProcessor(
    name="Nikto",
    summary_func=nikto_summary,
    html_func=generate_nikto_html_section,
    ai_normalizer=lambda findings: [
        {
            "tool": "Nikto",
            "severity": str(f.get("severity", f.get("Severity", "UNKNOWN"))).upper(),
            "rule_id": str(f.get("rule_id", f.get("id", ""))),
            "path": str(f.get("path", f.get("file", f.get("filename", "")))),
            "line": str(f.get("line", f.get("line_number", f.get("start", "")))),
            "message": str(f.get("message", f.get("description", f.get("title", "")))),
        }
        for f in (findings or [])
    ],
    json_file="nikto.json",
)