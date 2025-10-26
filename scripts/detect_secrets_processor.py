#!/usr/bin/env python3
import sys
import html
import json

# Add parent directory to path for imports
sys.path.insert(0, '/SimpleSecCheck')

pass

def debug(msg):
    print(f"[detect_secrets_processor] {msg}", file=sys.stderr)

def detect_secrets_summary(detect_secrets_json):
    findings = []
    if detect_secrets_json and isinstance(detect_secrets_json, dict):
        results = detect_secrets_json.get('results', [])
        for filename, file_results in results.items():
            if isinstance(file_results, list):
                for r in file_results:
                    finding = {
                        'filename': filename,
                        'line_number': r.get('line_number', 0),
                        'type': r.get('type', ''),
                        'hashed_secret': r.get('hashed_secret', ''),
                        'is_secret': r.get('is_secret', False),
                        'is_verified': r.get('is_verified', False)
                    }
                    findings.append(finding)
    elif isinstance(detect_secrets_json, str):
        # Try to parse JSON string
        try:
            data = json.loads(detect_secrets_json)
            if isinstance(data, dict):
                results = data.get('results', [])
                for filename, file_results in results.items():
                    if isinstance(file_results, list):
                        for r in file_results:
                            finding = {
                                'filename': filename,
                                'line_number': r.get('line_number', 0),
                                'type': r.get('type', ''),
                                'hashed_secret': r.get('hashed_secret', ''),
                                'is_secret': r.get('is_secret', False),
                                'is_verified': r.get('is_verified', False)
                            }
                            findings.append(finding)
        except json.JSONDecodeError:
            debug("Failed to parse detect-secrets JSON as string.")
    else:
        debug("No detect-secrets results found in JSON.")
    return findings

def generate_detect_secrets_html_section(detect_secrets_findings):
    html_parts = []
    html_parts.append('<h2>Detect-secrets Secret Detection</h2>')
    if detect_secrets_findings:
        html_parts.append('<table><tr><th>Type</th><th>File</th><th>Line</th><th>Verified</th></tr>')
        for finding in detect_secrets_findings:
            verified = 'Yes' if finding.get('is_verified', False) else 'No'
            icon = '🚨' if finding.get('is_verified', False) else '⚠️'
            type_escaped = html.escape(str(finding.get("type", "")))
            filename_escaped = html.escape(str(finding.get("filename", "")))
            line_escaped = html.escape(str(finding.get("line_number", "")))
            verified_escaped = html.escape(str(verified))
            
            html_parts.append(f'<tr><td>{type_escaped}</td><td>{filename_escaped}</td><td>{line_escaped}</td><td>{verified_escaped} {icon}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No secrets detected.</div>')
    return "".join(html_parts)

