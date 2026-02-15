#!/usr/bin/env python3
import sys
import json
import html
import os

def debug(msg):
    print(f"[bandit_processor] {msg}", file=sys.stderr)

def load_bandit_results(json_file):
    """Load Bandit JSON results file"""
    if not os.path.exists(json_file):
        debug(f"Bandit results file not found: {json_file}")
        return None
    
    try:
        with open(json_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        debug(f"Error loading Bandit results: {e}")
        return None

def bandit_summary(bandit_data):
    """Extract summary from Bandit results"""
    findings = []
    if bandit_data and 'results' in bandit_data:
        for result in bandit_data['results']:
            findings.append({
                'test_id': result.get('test_id', ''),
                'test_name': result.get('test_name', ''),
                'severity': result.get('issue_severity', ''),
                'confidence': result.get('issue_confidence', ''),
                'filename': result.get('filename', ''),
                'line_number': result.get('line_number', ''),
                'code': result.get('code', ''),
                'message': result.get('issue_text', '')
            })
    else:
        debug("No Bandit results found in JSON.")
    return findings

def generate_bandit_html_section(bandit_findings):
    """Generate HTML section for Bandit findings"""
    html_parts = []
    html_parts.append('<h2>Bandit Python Security Scan</h2>')
    
    if bandit_findings:
        html_parts.append('<table><tr><th>Test ID</th><th>Severity</th><th>Confidence</th><th>File</th><th>Line</th><th>Issue</th><th>Code</th></tr>')
        for finding in bandit_findings:
            sev = finding['severity'].upper() if finding['severity'] else 'UNKNOWN'
            icon = ''
            if sev == 'HIGH': icon = '🚨'
            elif sev == 'MEDIUM': icon = '⚠️'
            elif sev == 'LOW': icon = 'ℹ️'
            else: icon = 'ℹ️'
            
            filename_escaped = html.escape(str(finding['filename']))
            line_escaped = html.escape(str(finding['line_number']))
            test_id_escaped = html.escape(str(finding['test_id']))
            message_escaped = html.escape(str(finding['message']))
            code_escaped = html.escape(str(finding['code']))
            
            html_parts.append(f'<tr><td>{test_id_escaped}</td><td>{icon} {sev}</td><td>{finding["confidence"]}</td><td>{filename_escaped}</td><td>{line_escaped}</td><td>{message_escaped}</td><td>{code_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<p>No Python security vulnerabilities found.</p>')
    
    return '\n'.join(html_parts)

# Main processing logic
if __name__ == "__main__":
    results_dir = sys.argv[1] if len(sys.argv) > 1 else "/SimpleSecCheck/results"
    bandit_json_file = os.path.join(results_dir, 'bandit.json')
    
    bandit_data = load_bandit_results(bandit_json_file)
    if bandit_data:
        findings = bandit_summary(bandit_data)
        html_section = generate_bandit_html_section(findings)
        print(html_section)

