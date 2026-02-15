#!/usr/bin/env python3
import sys
import html
import json

# Add parent directory to path for imports
sys.path.insert(0, '/SimpleSecCheck')

pass

def debug(msg):
    print(f"[brakeman_processor] {msg}", file=sys.stderr)

def brakeman_summary(brakeman_json):
    findings = []
    if brakeman_json and isinstance(brakeman_json, dict):
        # Parse Brakeman JSON output
        warnings = brakeman_json.get('warnings', [])
        for warning in warnings:
            finding = {
                'warning_type': warning.get('warning_type', ''),
                'warning_code': warning.get('warning_code', ''),
                'message': warning.get('message', ''),
                'file': warning.get('file', ''),
                'line': warning.get('line', ''),
                'link': warning.get('link', ''),
                'confidence': warning.get('confidence', ''),
                'description': warning.get('description', '')
            }
            findings.append(finding)
    else:
        debug("No Brakeman results found in JSON.")
    return findings

def generate_brakeman_html_section(brakeman_findings):
    html_parts = []
    html_parts.append('<h2>Brakeman Ruby on Rails Security Scan</h2>')
    if brakeman_findings:
        html_parts.append('<table><tr><th>Type</th><th>Confidence</th><th>File</th><th>Line</th><th>Message</th></tr>')
        for finding in brakeman_findings:
            type_escaped = html.escape(str(finding.get('warning_type', '')))
            confidence_escaped = html.escape(str(finding.get('confidence', '')))
            file_escaped = html.escape(str(finding.get('file', '')))
            line_escaped = html.escape(str(finding.get('line', '')))
            message_escaped = html.escape(str(finding.get('message', '')))
            
            # Add confidence icons
            icon = ''
            conf_class = confidence_escaped.upper()
            if conf_class in ('HIGH', 'CERTAIN'): 
                icon = '🔴'
            elif conf_class == 'MEDIUM': 
                icon = '🟡'
            elif conf_class == 'WEAK': 
                icon = '🟢'
            
            html_parts.append(f'<tr class="row-{conf_class}"><td>{type_escaped}</td><td>{confidence_escaped} {icon}</td><td>{file_escaped}</td><td>{line_escaped}</td><td>{message_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No Ruby security vulnerabilities found.</div>')
    return "".join(html_parts)

