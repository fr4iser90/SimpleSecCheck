#!/usr/bin/env python3
import sys

def debug(msg):
    print(f"[trivy_processor] {msg}", file=sys.stderr)

def trivy_summary(trivy_json):
    vulns = []
    if trivy_json and 'Results' in trivy_json:
        for result in trivy_json['Results']:
            for v in result.get('Vulnerabilities', []):
                vulns.append({
                    'PkgName': v.get('PkgName', ''),
                    'Severity': v.get('Severity', ''),
                    'VulnerabilityID': v.get('VulnerabilityID', ''),
                    'Title': v.get('Title', ''),
                    'Description': v.get('Description', '')
                })
    else:
        debug("No Trivy results found in JSON.")
    return vulns

def generate_trivy_html_section(trivy_vulns):
    html_parts = []
    html_parts.append('<h2>Trivy Dependency & Container Scan</h2>')
    if trivy_vulns:
        html_parts.append('<table><tr><th>Package</th><th>Severity</th><th>CVE</th><th>Title</th></tr>')
        for v in trivy_vulns:
            sev = v['Severity'].upper()
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
                pkg_name_escaped = html.escape(str(v["PkgName"]))
                sev_escaped = html.escape(str(sev))
                vuln_id_escaped = html.escape(str(v["VulnerabilityID"]))
                title_escaped = html.escape(str(v["Title"]))
            except ImportError:
                pkg_name_escaped = str(v["PkgName"]).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                sev_escaped = str(sev).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                vuln_id_escaped = str(v["VulnerabilityID"]).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                title_escaped = str(v["Title"]).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

            html_parts.append(f'<tr class="row-{sev_escaped}"><td>{pkg_name_escaped}</td><td class="severity-{sev_escaped}">{icon} {sev_escaped}</td><td>{vuln_id_escaped}</td><td>{title_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No vulnerabilities found in dependencies or containers.</div>')
    return "".join(html_parts) 