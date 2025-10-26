#!/usr/bin/env python3
import sys
import html

def debug(msg):
    print(f"[wapiti_processor] {msg}", file=sys.stderr)

def wapiti_summary(wapiti_json):
    findings = []
    if wapiti_json and isinstance(wapiti_json, dict):
        # Wapiti JSON structure: vulnerabilities is a dict of {vuln_type: {url: [info]}}
        vulnerabilities = wapiti_json.get('vulnerabilities', {})
        if isinstance(vulnerabilities, dict):
            for vuln_type, vuln_data in vulnerabilities.items():
                if isinstance(vuln_data, dict):
                    for url, vuln_details in vuln_data.items():
                        if isinstance(vuln_details, list):
                            for vuln in vuln_details:
                                if isinstance(vuln, dict):
                                    finding = {
                                        'category': vuln_type,
                                        'description': vuln.get('desc', vuln.get('description', '')),
                                        'reference': str(vuln.get('ref', {})),
                                        'target': url,
                                        'info': vuln
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

