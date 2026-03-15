#!/usr/bin/env python3
from scanner.output.processor_registry import ReportProcessor
import sys
import html
import json

# Add parent directory to path for imports
# Setup paths using central path_setup module
# NO PATH CALCULATIONS HERE - everything is handled by path_setup.py
sys.path.insert(0, "/project/src")
sys.path.insert(0, "/app")  # For import
from core.path_setup import setup_paths
setup_paths()

pass

def debug(msg):
    print(f"[trufflehog_processor] {msg}", file=sys.stderr)

def trufflehog_summary(trufflehog_json):
    findings = []
    if trufflehog_json and isinstance(trufflehog_json, list):
        for r in trufflehog_json:
            source_meta = r.get('SourceMetadata', {}) or {}
            source_data = source_meta.get('Data', {}) if isinstance(source_meta, dict) else {}
            filesystem = source_data.get('Filesystem', {}) if isinstance(source_data, dict) else {}
            file_path = filesystem.get('file', '') if isinstance(filesystem, dict) else ''
            line = filesystem.get('line', '') if isinstance(filesystem, dict) else ''
            redacted = r.get('Redacted', '')
            raw_value = r.get('Raw', '')

            details_parts = []
            if file_path:
                details_parts.append(f"{file_path}:{line}" if line else file_path)
            if redacted or raw_value:
                details_parts.append(redacted or raw_value)

            finding = {
                'detector': r.get('DetectorName', ''),
                'verified': r.get('Verified', False),
                'raw': r.get('Raw', ''),
                'redacted': r.get('Redacted', ''),
                'extra_data': r.get('ExtraData', {}),
                'source_metadata': r.get('SourceMetadata', {}),
                'details': " | ".join(details_parts)
            }
            findings.append(finding)
    elif trufflehog_json and isinstance(trufflehog_json, str):
        # Try to parse JSON string
        try:
            data = json.loads(trufflehog_json)
            if isinstance(data, list):
                for r in data:
                    source_meta = r.get('SourceMetadata', {}) or {}
                    source_data = source_meta.get('Data', {}) if isinstance(source_meta, dict) else {}
                    filesystem = source_data.get('Filesystem', {}) if isinstance(source_data, dict) else {}
                    file_path = filesystem.get('file', '') if isinstance(filesystem, dict) else ''
                    line = filesystem.get('line', '') if isinstance(filesystem, dict) else ''
                    redacted = r.get('Redacted', '')
                    raw_value = r.get('Raw', '')

                    details_parts = []
                    if file_path:
                        details_parts.append(f"{file_path}:{line}" if line else file_path)
                    if redacted or raw_value:
                        details_parts.append(redacted or raw_value)

                    finding = {
                        'detector': r.get('DetectorName', ''),
                        'verified': r.get('Verified', False),
                        'raw': r.get('Raw', ''),
                        'redacted': r.get('Redacted', ''),
                        'extra_data': r.get('ExtraData', {}),
                        'source_metadata': r.get('SourceMetadata', {}),
                        'details': " | ".join(details_parts)
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
            details_text = finding.get("details", "")
            if not details_text:
                extra_data = finding.get("extra_data") or {}
                details_text = extra_data.get("message", "") if isinstance(extra_data, dict) else ""
            details_escaped = html.escape(str(details_text))
            
            html_parts.append(f'<tr><td>{detector_escaped}</td><td>{verified_escaped} {icon}</td><td>{details_escaped}</td></tr>')
        html_parts.append('</table>')
    else:
        html_parts.append('<div class="all-clear"><span class="icon sev-PASSED">✅</span> All clear! No secrets detected.</div>')
    return "".join(html_parts)

REPORT_PROCESSOR = ReportProcessor(
    name="TruffleHog",
    summary_func=trufflehog_summary,
    html_func=generate_trufflehog_html_section,
    ai_normalizer=lambda findings: [
        {
            "tool": "TruffleHog",
            "severity": str(f.get("severity", f.get("Severity", "UNKNOWN"))).upper(),
            "rule_id": str(f.get("rule_id", f.get("id", ""))),
            "path": str(f.get("path", f.get("file", f.get("filename", "")))),
            "line": str(f.get("line", f.get("line_number", f.get("start", "")))),
            "message": str(f.get("message", f.get("description", f.get("title", "")))),
        }
        for f in (findings or [])
    ],
    json_file="report.json",  # Changed from trufflehog.json
)