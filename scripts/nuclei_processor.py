#!/usr/bin/env python3
import sys
import html

def debug(msg):
    print(f"[nuclei_processor] {msg}", file=sys.stderr)

def nuclei_summary(nuclei_json):
    findings = []
    if nuclei_json and isinstance(nuclei_json, list):
        for r in nuclei_json:
            finding = {
                'template_id': r.get('template-id', ''),
                'name': r.get('name', ''),
                'host': r.get('host', ''),
                'matched_at': r.get('matched-at', ''),
                'severity': r.get('info', {}).get('severity', ''),
                'description': r.get('info', {}).get('description', ''),
                'reference': r.get('info', {}).get('reference', ''),
                'tags': r.get('info', {}).get('tags', [])
            }
            findings.append(finding)
    else:
        debug("No Nuclei results found in JSON.")
    return findings

def generate_nuclei_html_section(nuclei_findings):
    html_parts = []
    html_parts.append('<h2>Nuclei Web Application Security Scan</h2>')
    if nuclei_findings:
        html_parts.append('<table><tr><th>Template</th><th>Host</th><th>Severity</th><th>Description</th></tr>')
        for finding in nuclei_findings:
            sev = finding['severity'].upper()
            icon = ''
            if sev == 'CRITICAL': icon = '🚨'
            elif sev == 'HIGH': icon = '🚨'
            elif sev == 'MEDIUM': icon = '⚠️'
            elif sev == 'LOW': icon = 'ℹ️'
            elif sev in ('INFO', 'INFORMATIONAL'): icon = 'ℹ️'
            
            template_id_escaped = html.escape(str(finding.get("template_id", "")))
            host_escaped = html.escape(str(finding.get("host", "")))
            sev_escaped = html.escape(str(sev))
            description_escaped = html.escape(str(finding.get("description", "")))

            html_parts.append(f'<tr class="row-{sev_escaped}"><td>{template_id_escaped}</td><td>{host_escaped}</td><td class="severity-{sev_escaped}">{icon} {sev_escaped}</td><td>{description_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No web application vulnerabilities found.</div>')
    return "".join(html_parts)
