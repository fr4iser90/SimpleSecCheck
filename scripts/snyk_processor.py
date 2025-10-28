#!/usr/bin/env python3
import sys
import html
import json

def debug(msg):
    print(f"[snyk_processor] {msg}", file=sys.stderr)

def snyk_summary(snyk_json):
    findings = []
    if snyk_json and isinstance(snyk_json, dict):
        # Check if Snyk was skipped
        if snyk_json.get('skipped'):
            return None  # Return None to indicate skipped
        
        # Handle Snyk JSON format
        vulnerabilities = snyk_json.get('vulnerabilities', [])
        
        for vuln in vulnerabilities:
            finding = {
                'package': vuln.get('package', ''),
                'version': vuln.get('version', ''),
                'vulnerability_id': vuln.get('id', ''),
                'severity': vuln.get('severity', 'MEDIUM'),
                'title': vuln.get('title', ''),
                'description': vuln.get('description', ''),
                'cve': vuln.get('cve', ''),
                'cwe': vuln.get('cwe', ''),
                'cvss_score': vuln.get('cvssScore', ''),
                'exploit_maturity': vuln.get('exploitMaturity', ''),
                'language': vuln.get('language', ''),
                'package_manager': vuln.get('packageManager', ''),
                'semver': vuln.get('semver', {}),
                'from': vuln.get('from', []),
                'upgrade_path': vuln.get('upgradePath', []),
                'is_patchable': vuln.get('isPatchable', False),
                'is_upgradable': vuln.get('isUpgradable', False),
                'identifiers': vuln.get('identifiers', {}),
                'references': vuln.get('references', []),
                'credit': vuln.get('credit', []),
                'patches': vuln.get('patches', []),
                'disclosure_time': vuln.get('disclosureTime', ''),
                'publication_time': vuln.get('publicationTime', ''),
                'modification_time': vuln.get('modificationTime', '')
            }
            findings.append(finding)
    else:
        debug("No Snyk results found in JSON.")
    return findings

def generate_snyk_html_section(snyk_findings):
    html_parts = []
    html_parts.append('<h2>Snyk Vulnerability Scan</h2>')
    
    # Check if Snyk was skipped
    if snyk_findings is None:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">⏭️</span> Snyk scan was skipped. Set SNYK_TOKEN environment variable to enable Snyk vulnerability scanning.</div>')
        return "".join(html_parts)
    
    if snyk_findings and len(snyk_findings) > 0:
        html_parts.append('<table><tr><th>Package</th><th>Version</th><th>Vulnerability ID</th><th>Severity</th><th>Title</th><th>CVSS Score</th></tr>')
        for finding in snyk_findings:
            sev = finding['severity'].upper()
            icon = ''
            if sev == 'CRITICAL': icon = '🚨'
            elif sev == 'HIGH': icon = '🚨'
            elif sev == 'MEDIUM': icon = '⚠️'
            elif sev == 'LOW': icon = 'ℹ️'
            elif sev in ('INFO', 'INFORMATIONAL'): icon = 'ℹ️'
            
            cvss_score = finding.get('cvss_score', 'N/A')
            
            package_escaped = html.escape(str(finding.get("package", "")))
            version_escaped = html.escape(str(finding.get("version", "")))
            vuln_id_escaped = html.escape(str(finding.get("vulnerability_id", "")))
            sev_escaped = html.escape(str(sev))
            title_escaped = html.escape(str(finding.get("title", "")))
            cvss_escaped = html.escape(str(cvss_score))

            html_parts.append(f'<tr class="row-{sev_escaped}"><td>{package_escaped}</td><td>{version_escaped}</td><td>{vuln_id_escaped}</td><td class="severity-{sev_escaped}">{icon} {sev_escaped}</td><td>{title_escaped}</td><td>{cvss_escaped}</td></tr>')
        html_parts.append('</table>')
        
        # Add summary statistics
        severity_counts = {}
        for finding in snyk_findings:
            sev = finding['severity'].upper()
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        html_parts.append('<div class="summary-stats">')
        html_parts.append('<h3>Vulnerability Summary</h3>')
        html_parts.append('<ul>')
        for sev, count in severity_counts.items():
            html_parts.append(f'<li>{sev}: {count} vulnerabilities</li>')
        html_parts.append(f'<li><strong>Total: {len(snyk_findings)} vulnerabilities</strong></li>')
        html_parts.append('</ul>')
        html_parts.append('</div>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No vulnerabilities found by Snyk.</div>')
    return "".join(html_parts)
