#!/usr/bin/env python3
import sys
import html

def debug(msg):
    print(f"[wapiti_processor] {msg}", file=sys.stderr)

def wapiti_summary(wapiti_json):
    findings = []
    if wapiti_json and isinstance(wapiti_json, dict):
        vulnerabilities = wapiti_json.get('vulnerabilities', [])
        for vuln in vulnerabilities:
            finding = {
                'category': vuln.get('category', ''),
                'description': vuln.get('description', ''),
                'reference': vuln.get('reference', ''),
                'status': vuln.get('status', ''),
                'target': vuln.get('target', '')
            }
            findings.append(finding)
    else:
        debug("No Wapiti results found in JSON.")
    return findings

def generate_wapiti_html_section(wapiti_findings):
    html_parts = []
    html_parts.append('<h2>Wapiti Web Vulnerability Scan</h2>')
    if wapiti_findings:
        html_parts.append('<table><tr><th>Category</th><th>Description</th><th>Target</th></tr>')
        for finding in wapiti_findings:
            category_escaped = html.escape(str(finding.get('category', '')))
            description_escaped = html.escape(str(finding.get('description', '')))
            target_escaped = html.escape(str(finding.get('target', '')))
            html_parts.append(f'<tr><td>{category_escaped}</td><td>{description_escaped}</td><td>{target_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No vulnerabilities found.</div>')
    return "".join(html_parts)

