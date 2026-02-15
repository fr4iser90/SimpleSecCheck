#!/usr/bin/env python3
import sys
import html

def debug(msg):
    print(f"[checkov_processor] {msg}", file=sys.stderr)

def checkov_summary(checkov_json):
    findings = []
    if checkov_json and isinstance(checkov_json, dict):
        # Handle Checkov JSON format
        results = checkov_json.get('results', {})
        failed_checks = results.get('failed_checks', [])
        
        for check in failed_checks:
            finding = {
                'check_id': check.get('check_id', ''),
                'check_name': check.get('check_name', ''),
                'resource': check.get('resource', ''),
                'file_path': check.get('file_path', ''),
                'line_number': check.get('file_line_range', [0])[0] if check.get('file_line_range') else 0,
                'severity': 'HIGH' if 'HIGH' in check.get('check_name', '') or 'CRITICAL' in check.get('check_name', '') else 'MEDIUM',
                'description': check.get('guideline', ''),
                'code_block': check.get('code_block', []),
                'fix': check.get('code_block', []),
                'framework': check.get('check_id', '').split('_')[0] if check.get('check_id', '') else 'UNKNOWN'
            }
            
            findings.append(finding)
    else:
        debug("No Checkov results found in JSON.")
    return findings

def generate_checkov_html_section(checkov_findings):
    html_parts = []
    html_parts.append('<h2>Checkov Infrastructure Security Scan</h2>')
    if checkov_findings:
        html_parts.append('<table><tr><th>Check ID</th><th>Check Name</th><th>Framework</th><th>Resource</th><th>File</th><th>Severity</th><th>Description</th></tr>')
        for finding in checkov_findings:
            sev = finding['severity'].upper()
            icon = ''
            if sev == 'CRITICAL': icon = '🚨'
            elif sev == 'HIGH': icon = '🚨'
            elif sev == 'MEDIUM': icon = '⚠️'
            elif sev == 'LOW': icon = 'ℹ️'
            elif sev in ('INFO', 'INFORMATIONAL'): icon = 'ℹ️'
            
            check_id_escaped = html.escape(str(finding.get("check_id", "")))
            check_name_escaped = html.escape(str(finding.get("check_name", "")))
            framework_escaped = html.escape(str(finding.get("framework", "UNKNOWN")))
            resource_escaped = html.escape(str(finding.get("resource", "")))
            file_path_escaped = html.escape(str(finding.get("file_path", "")))
            sev_escaped = html.escape(str(sev))
            desc_escaped = html.escape(str(finding.get("description", "")))

            html_parts.append(f'<tr class="row-{sev_escaped}"><td>{check_id_escaped}</td><td>{check_name_escaped}</td><td>{framework_escaped}</td><td>{resource_escaped}</td><td>{file_path_escaped}</td><td class="severity-{sev_escaped}">{icon} {sev_escaped}</td><td>{desc_escaped}</td></tr>')
        html_parts.append('</table>')
        
        # Add summary statistics
        severity_counts = {}
        framework_counts = {}
        for finding in checkov_findings:
            sev = finding['severity'].upper()
            framework = finding.get('framework', 'UNKNOWN')
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
            framework_counts[framework] = framework_counts.get(framework, 0) + 1
        
        html_parts.append('<div class="summary-stats">')
        html_parts.append('<h3>Security Issue Summary</h3>')
        html_parts.append('<ul>')
        for sev, count in severity_counts.items():
            html_parts.append(f'<li>{sev}: {count} issues</li>')
        html_parts.append(f'<li><strong>Total: {len(checkov_findings)} infrastructure security issues</strong></li>')
        html_parts.append('</ul>')
        
        html_parts.append('<h3>Issues by Framework</h3>')
        html_parts.append('<ul>')
        for framework, count in framework_counts.items():
            html_parts.append(f'<li>{framework}: {count} issues</li>')
        html_parts.append('</ul>')
        html_parts.append('</div>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No infrastructure security issues found by Checkov.</div>')
    return "".join(html_parts)

