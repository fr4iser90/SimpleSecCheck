#!/usr/bin/env python3
import sys

def debug(msg):
    print(f"[anchore_processor] {msg}", file=sys.stderr)

def anchore_summary(anchore_json):
    vulns = []
    if anchore_json and 'matches' in anchore_json:
        for match in anchore_json['matches']:
            vulns.append({
                'PkgName': match.get('artifact', {}).get('name', ''),
                'Severity': match.get('vulnerability', {}).get('severity', ''),
                'VulnerabilityID': match.get('vulnerability', {}).get('id', ''),
                'Title': match.get('vulnerability', {}).get('description', ''),
                'Description': match.get('vulnerability', {}).get('description', '')
            })
    else:
        debug("No Anchore results found in JSON.")
    return vulns

def generate_anchore_html_section(anchore_vulns):
    html_parts = []
    html_parts.append('<h2>Anchore Container Image Vulnerability Scan</h2>')
    
    # Check if there's a note about setup requirements
    if not anchore_vulns or (anchore_vulns and len(anchore_vulns) == 0):
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No vulnerabilities found in container image.</div>')
    elif anchore_vulns:
        html_parts.append('<table><tr><th>Package</th><th>Severity</th><th>CVE</th><th>Title</th></tr>')
        for v in anchore_vulns:
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

