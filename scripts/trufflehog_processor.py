#!/usr/bin/env python3
import sys
import html
import json

# Add parent directory to path for imports
sys.path.insert(0, '/SimpleSecCheck')

pass

def debug(msg):
    print(f"[trufflehog_processor] {msg}", file=sys.stderr)

def trufflehog_summary(trufflehog_json):
    findings = []
    if trufflehog_json and isinstance(trufflehog_json, list):
        for r in trufflehog_json:
            finding = {
                'detector': r.get('DetectorName', ''),
                'verified': r.get('Verified', False),
                'raw': r.get('Raw', ''),
                'redacted': r.get('Redacted', ''),
                'extra_data': r.get('ExtraData', {}),
                'source_metadata': r.get('SourceMetadata', {})
            }
            findings.append(finding)
    elif trufflehog_json and isinstance(trufflehog_json, str):
        # Try to parse JSON string
        try:
            data = json.loads(trufflehog_json)
            if isinstance(data, list):
                for r in data:
                    finding = {
                        'detector': r.get('DetectorName', ''),
                        'verified': r.get('Verified', False),
                        'raw': r.get('Raw', ''),
                        'redacted': r.get('Redacted', ''),
                        'extra_data': r.get('ExtraData', {}),
                        'source_metadata': r.get('SourceMetadata', {})
                    }
                    findings.append(finding)
        except json.JSONDecodeError:
            debug("Failed to parse TruffleHog JSON as string.")
    else:
        debug("No TruffleHog results found in JSON.")
    return findings

def generate_trufflehog_html_section(trufflehog_findings):
    html_parts = []
    html_parts.append('<h2>TruffleHog Secret Detection</h2>')
    if trufflehog_findings:
        html_parts.append('<table><tr><th>Detector</th><th>Verified</th><th>Details</th></tr>')
        for finding in trufflehog_findings:
            verified = 'Yes' if finding.get('verified', False) else 'No'
            icon = '🚨' if finding.get('verified', False) else '⚠️'
            detector_escaped = html.escape(str(finding.get("detector", "")))
            verified_escaped = html.escape(str(verified))
            # Safely handle extra_data - it might be None or missing
            extra_data = finding.get("extra_data") or {}
            details_escaped = html.escape(str(extra_data.get("message", "") if isinstance(extra_data, dict) else ""))
            
            html_parts.append(f'<tr><td>{detector_escaped}</td><td>{verified_escaped} {icon}</td><td>{details_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No secrets detected.</div>')
    return "".join(html_parts)
