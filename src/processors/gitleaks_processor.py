#!/usr/bin/env python3
import sys
import html
import json

# Add parent directory to path for imports
sys.path.insert(0, '/SimpleSecCheck')

pass

def debug(msg):
    print(f"[gitleaks_processor] {msg}", file=sys.stderr)

def gitleaks_summary(gitleaks_json):
    findings = []
    if gitleaks_json and isinstance(gitleaks_json, list):
        for r in gitleaks_json:
            finding = {
                'rule_id': r.get('RuleID', ''),
                'description': r.get('Description', ''),
                'file': r.get('File', ''),
                'line': r.get('StartLine', 0),
                'secret': r.get('Secret', ''),
                'commit': r.get('Commit', ''),
                'author': r.get('Author', ''),
                'date': r.get('Date', '')
            }
            findings.append(finding)
    elif gitleaks_json and isinstance(gitleaks_json, str):
        # Try to parse JSON string
        try:
            data = json.loads(gitleaks_json)
            if isinstance(data, list):
                for r in data:
                    finding = {
                        'rule_id': r.get('RuleID', ''),
                        'description': r.get('Description', ''),
                        'file': r.get('File', ''),
                        'line': r.get('StartLine', 0),
                        'secret': r.get('Secret', ''),
                        'commit': r.get('Commit', ''),
                        'author': r.get('Author', ''),
                        'date': r.get('Date', '')
                    }
                    findings.append(finding)
        except json.JSONDecodeError:
            debug("Failed to parse GitLeaks JSON as string.")
    else:
        debug("No GitLeaks results found in JSON.")
    return findings

def generate_gitleaks_html_section(gitleaks_findings):
    html_parts = []
    html_parts.append('<h2>GitLeaks Secret Detection</h2>')
    if gitleaks_findings:
        html_parts.append('<table><tr><th>Rule ID</th><th>File</th><th>Line</th><th>Description</th></tr>')
        for finding in gitleaks_findings:
            rule_id_escaped = html.escape(str(finding.get("rule_id", "")))
            file_escaped = html.escape(str(finding.get("file", "")))
            line_escaped = html.escape(str(finding.get("line", "")))
            description_escaped = html.escape(str(finding.get("description", "")))
            
            html_parts.append(f'<tr><td>{rule_id_escaped}</td><td>{file_escaped}</td><td>{line_escaped}</td><td>{description_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No secrets detected.</div>')
    return "".join(html_parts)

