#!/usr/bin/env python3
from scanner.output.processor_registry import ReportProcessor
import sys

def debug(msg):
    print(f"[clair_processor] {msg}", file=sys.stderr)

def clair_summary(clair_json):
    vulns = []
    if clair_json and 'vulnerabilities' in clair_json:
        for v in clair_json['vulnerabilities']:
            vulns.append({
                'PkgName': v.get('package', ''),
                'Severity': v.get('severity', ''),
                'VulnerabilityID': v.get('vulnerability', ''),
                'Title': v.get('title', ''),
                'Description': v.get('description', '')
            })
    else:
        debug("No Clair results found in JSON.")
    return vulns

def generate_clair_html_section(clair_vulns):
    html_parts = []
    html_parts.append('<h2>Clair Container Image Vulnerability Scan</h2>')
    
    # Check if there's a note about setup requirements
    if not clair_vulns or (clair_vulns and len(clair_vulns) == 0):
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No vulnerabilities found in container image.</div>')
    elif clair_vulns:
        html_parts.append('<table><tr><th>Package</th><th>Severity</th><th>CVE</th><th>Title</th></tr>')
        for v in clair_vulns:
            sev = v.get('Severity', 'UNKNOWN').upper()
            icon = ''
            if sev == 'CRITICAL': icon = '🚨'
            elif sev == 'HIGH': icon = '🚨'
            elif sev == 'MEDIUM': icon = '⚠️'
            elif sev == 'LOW': icon = 'ℹ️'
            elif sev in ('INFO', 'INFORMATIONAL'): icon = 'ℹ️'
            
            # Basic HTML escaping
            pkg_name_escaped = sev_escaped = vuln_id_escaped = title_escaped = ""
            try:
                import html
                pkg_name_escaped = html.escape(str(v.get("PkgName", "")))
                sev_escaped = html.escape(str(sev))
                vuln_id_escaped = html.escape(str(v.get("VulnerabilityID", "")))
                title_escaped = html.escape(str(v.get("Title", "")))
            except ImportError:
                pkg_name_escaped = str(v.get("PkgName", "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                sev_escaped = str(sev).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                vuln_id_escaped = str(v.get("VulnerabilityID", "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                title_escaped = str(v.get("Title", "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

            html_parts.append(f'<tr class="row-{sev_escaped}"><td>{pkg_name_escaped}</td><td class="severity-{sev_escaped}">{icon} {sev_escaped}</td><td>{vuln_id_escaped}</td><td>{title_escaped}</td></tr>')
        html_parts.append('</table>')
    
    return "".join(html_parts)

REPORT_PROCESSOR = ReportProcessor(
    name="Clair",
    summary_func=clair_summary,
    html_func=generate_clair_html_section,
    ai_normalizer=lambda findings: [
        {
            "tool": "Clair",
            "severity": str(f.get("severity", f.get("Severity", "UNKNOWN"))).upper(),
            "rule_id": str(f.get("rule_id", f.get("id", ""))),
            "path": str(f.get("path", f.get("file", f.get("filename", "")))),
            "line": str(f.get("line", f.get("line_number", f.get("start", "")))),
            "message": str(f.get("message", f.get("description", f.get("title", "")))),
        }
        for f in (findings or [])
    ],
    json_file="report.json",  # Changed from clair.json
)